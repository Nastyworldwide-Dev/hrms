<!--
  GPullRefresh — pull to refresh (spec §10.3 treatment list). Wraps
  ion-refresher; does not replace it. ListView.vue is NOT modified.

  WHAT IS AND IS NOT REACHABLE — reported rather than worked around:
  ion-refresher-content renders its pulling icon and refreshing spinner inside
  shadow DOM, and Ionic publishes NO CSS custom properties and no ::part() for
  them. So they cannot be themed from the Glass layer, only switched off.
  That is what this does: `pulling-icon="none"` and `refreshing-spinner="none"`
  turn the un-themable nodes off — which §11.2 wants anyway ("no spinners
  anywhere in this app") — and the indicator below is ours, in the light DOM,
  fully tokenised. The gesture, threshold and completion lifecycle stay
  Ionic's; only the visual is replaced.

  The indeterminate bar animates transform only (§8, §15) and goes static under
  prefers-reduced-motion.

  ionRefresh/ionStart wired by hand, NOT `@ionRefresh=`/`@ionStart=` (28 Sep
  2026, owner report: pull-to-refresh never actually reloaded anything). Ionic
  emits these with an exact camelCase name (createEvent(this, "ionRefresh", …)
  in @ionic/core); Vue's own runtime-dom hyphenates a template `@ionRefresh`
  binding down to a listener for "ion-refresh" before registering it
  (runtime-dom's parseName: hyphenate(name.slice(2))). The two never meet, so
  the handler silently never ran — proven on a live page: intercepting every
  addEventListener call showed "ion-refresh" registered while the element only
  ever dispatches "ionRefresh". A raw addEventListener with the literal name
  is the only binding that receives it.

  Props:
    pullingText     string, default "Pull to refresh"
    refreshingText  string, default "Refreshing…"
  Emits: refresh(event) — pass the event to complete(): event.target.complete()
-->
<template>
	<ion-refresher ref="refresherEl" slot="fixed" pulling-icon="none" :refreshing-spinner="null">
		<ion-refresher-content>
			<div class="g-refresh" role="status">
				<span class="g-refresh__bar" aria-hidden="true">
					<span class="g-refresh__fill" />
				</span>
				{{ refreshing ? refreshingText : pullingText }}
			</div>
		</ion-refresher-content>
	</ion-refresher>
</template>

<script setup>
import { onBeforeUnmount, onMounted, ref } from "vue"
import { IonRefresher, IonRefresherContent } from "@ionic/vue"

defineProps({
	pullingText: { type: String, default: "Pull to refresh" },
	refreshingText: { type: String, default: "Refreshing…" },
})
const emit = defineEmits(["refresh"])

const refreshing = ref(false)
const refresherEl = ref(null)
// A page completes the pull after its reload; if that reload rejects or hangs,
// nothing would ever close the refresher. Ionic's own close is idempotent.
const COMPLETE_CAP_MS = 10000
let capTimer = null

// Ionic 7 sends no event when a refresh completes (only ionRefresh, ionPull,
// ionStart), so the label resets when the next pull starts instead.
function onStart() {
	refreshing.value = false
}

function onRefresh(event) {
	refreshing.value = true
	console.info("[GPullRefresh] refresh started")
	clearTimeout(capTimer)
	capTimer = setTimeout(() => event.target?.complete?.(), COMPLETE_CAP_MS)
	emit("refresh", event)
}

//: The component ref is the Vue wrapper's public instance ($el is its root
//: DOM node — the real <ion-refresher>, the one thing that actually fires
//: these events), the same pattern ListView.vue already uses for ion-content.
function nativeEl() {
	return refresherEl.value?.$el ?? refresherEl.value
}

onMounted(() => {
	const el = nativeEl()
	if (!el) {
		console.warn("[GPullRefresh] ion-refresher element not found; refresh is inert")
		return
	}
	el.addEventListener("ionStart", onStart)
	el.addEventListener("ionRefresh", onRefresh)
})

onBeforeUnmount(() => {
	const el = nativeEl()
	el?.removeEventListener("ionStart", onStart)
	el?.removeEventListener("ionRefresh", onRefresh)
	clearTimeout(capTimer)
})
</script>
