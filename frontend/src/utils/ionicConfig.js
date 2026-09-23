import { isPlatform } from "@ionic/vue"
import { createAnimation, iosTransitionAnimation } from "@ionic/core"

import { isBrowserTraversal } from "@/utils/browserTraversal"
import { pickNavMotion } from "@/utils/navMotion"

const prefersReducedMotion = () =>
	typeof window !== "undefined" &&
	window.matchMedia?.("(prefers-reduced-motion: reduce)").matches === true

//: One builder for every device (audit F-4). It used to force the iPhone push
//: at 540 ms everywhere, desktop included, and only iPhones skipped the
//: double animation after a swipe back. The rule itself is utils/navMotion.js.
const animationBuilder = (baseEl, opts) => {
	const motion = pickNavMotion({
		reducedMotion: prefersReducedMotion(),
		width: typeof window === "undefined" ? 0 : window.innerWidth,
		ios: isPlatform("ios"),
		direction: opts.direction,
		gesture: isBrowserTraversal(),
	})
	if (motion.kind === "ios") return iosTransitionAnimation(baseEl, opts)
	if (motion.kind === "none") return createAnimation()
	return fadeThrough(opts, motion.duration)
}

//: Material 3 fade-through: the leaving page fades out, the entering page
//: fades in. No slide, so nothing reads as "going deeper" where it is not.
function fadeThrough(opts, duration) {
	const entering = createAnimation()
		.addElement(opts.enteringEl)
		.fromTo("opacity", "0", "1")
		.beforeRemoveClass("ion-page-invisible")
	const animation = createAnimation().duration(duration).easing("ease-out").addAnimation(entering)
	if (opts.leavingEl) {
		animation.addAnimation(
			createAnimation().addElement(opts.leavingEl).fromTo("opacity", "1", "0")
		)
	}
	return animation
}

const getIonicConfig = () => {
	const config = { mode: "ios", navAnimation: animationBuilder }
	if (isPlatform("iphone")) {
		// Safari animates its own edge-swipe back; Ionic's gesture would be a second.
		config.swipeBackEnabled = false
	}
	console.info("[ionicConfig] one navigation animation rule for every device")
	return config
}

export default getIonicConfig
