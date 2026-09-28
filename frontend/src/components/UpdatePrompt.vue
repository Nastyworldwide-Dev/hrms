<!--
  UpdatePrompt — a new build waits to be let in (pre-2.0 R3).

  The app shipped `registerType: "autoUpdate"` with `self.skipWaiting()` at the
  service worker's module scope, which together mean: the moment a new build
  finishes downloading, it activates and the page reloads. Mid-session.
  Mid-form. The employee typing a leave reason loses it to a reload nobody
  asked for, and cannot tell what happened.

  The checklist asks that update behaviour be CONTROLLED and that "new
  deployments do not leave users stuck on old broken assets". Those pull
  against each other, and the resolution is this: the new build is downloaded
  and ready immediately, and it takes the page when the employee says so. A
  reload they chose costs them nothing; one they did not costs them whatever
  they had typed.

  DISMISSIBLE, which it was not at first. The reasoning then was that closing
  it would strand the employee on the old build with no way back to the offer —
  the "stuck on old assets" half of the same rule. On a real phone that came
  out as a bar nobody could clear, sitting over the bottom of every screen
  (owner, 22 Sep 2026: "it kinda stuck ... cant swipe or clear that").
  The resolution is that dismissing is not refusing: the new build is still
  downloaded and still takes over on the NEXT full load, which on a PWA people
  leave open is the next time they cold-start it. So the offer can be put away
  without being lost.

  AND THE DISMISSAL HAD TO BE REMEMBERED. Reported 23 September 2026 — "the new
  version is still popping every time". Dismissing flipped a ref and nothing
  else: the waiting worker stayed waiting, so the next load registered it
  again, onNeedRefresh fired again, and the bar came back on every single
  reload until the employee gave in and tapped Reload. A dismissal the app
  forgets is not a dismissal; it is a delay.

  Remembered PER BUILD rather than for a period (see utils/updatePromptMemory):
  an update is a specific build, it stops mattering the moment a newer one
  lands, and a timed silence would hide a genuinely urgent fix.

  ONE WORKER, AND IT NAMES ITSELF (owner, 28 Sep 2026: "keeps appearing
  inappropriately"). This used to register the worker again through
  vite-plugin-pwa while main.js registered it with ?config=… — two URLs, one
  scope, each load installing the other as "waiting": the bar on every load
  with nothing deployed. And the build id was read from the worker's URL,
  which has been /hrms/sw.js for every build since alpha.12, so a dismissal
  saved nothing. Now main.js's one registration is watched, and the waiting
  build is asked for its own id (public/sw.js, GET_BUILD_ID).
-->
<template>
	<Transition name="g-update">
		<div v-if="needRefresh" class="g-update" role="status">
			<span class="g-update__text">{{ __("A new version is ready.") }}</span>
			<button type="button" class="g-update__action g-focusable" @click="reload">
				{{ __("Reload") }}
			</button>
			<button
				type="button"
				class="g-update__dismiss g-focusable"
				:aria-label="__('Not now')"
				@click="dismiss"
			>
				<X :size="16" />
			</button>
		</div>
	</Transition>
</template>

<script setup>
import { inject, ref, watch } from "vue"
import { X } from "lucide-vue-next"

import { swRegistration } from "@/data/swRegistration"
import { UPDATE_DISMISS_KEY, shouldOfferUpdate } from "@/utils/updatePromptMemory"

const __ = inject("$translate")

const needRefresh = ref(false)
//: The build currently waiting, as the build itself names it, so a dismissal
//: can name what it dismissed.
let waitingId = null
//: How long Reload waits for the new build to take control before reloading
//: anyway (hotfix 23 Sep: on a real phone that event never came, so Reload
//: did nothing and the bar kept returning).
const RELOAD_FALLBACK_MS = 3000
//: How long to wait for a waiting build to say which build it is.
const ASK_TIMEOUT_MS = 2000

//: Storage is a CONVENIENCE, never a dependency — private mode and cleared
//: site data both throw on access, and the update offer has to work anyway.
//: Failing to read means "not dismissed", which shows the bar: the safe
//: direction, since the other one strands somebody on a broken build.
function remembered() {
	try {
		return localStorage.getItem(UPDATE_DISMISS_KEY)
	} catch {
		return null
	}
}

function remember(id) {
	if (!id) return
	try {
		localStorage.setItem(UPDATE_DISMISS_KEY, id)
	} catch {
		// Nothing to do. The bar will be offered again next load, which is the
		// old behaviour and still correct — just noisier.
		console.info("[update] could not remember the dismissal; storage is unavailable")
	}
}

//: The waiting build names itself (public/sw.js answers GET_BUILD_ID from its
//: own precache). The worker's URL cannot: it is /hrms/sw.js for every build.
//: A build that does not answer (one from before this change) is null, which
//: is offered — the safe direction.
function askBuildId(worker) {
	return new Promise((resolve) => {
		const channel = new MessageChannel()
		const timer = setTimeout(() => resolve(null), ASK_TIMEOUT_MS)
		channel.port1.onmessage = (event) => {
			clearTimeout(timer)
			resolve(event.data?.buildId || null)
		}
		try {
			worker.postMessage({ type: "GET_BUILD_ID" }, [channel.port2])
		} catch {
			clearTimeout(timer)
			resolve(null)
		}
	})
}

//: A new version is a worker waiting BEHIND an active one. The very first
//: install has nothing to replace, and is not offered.
async function consider(registration) {
	const worker = registration?.waiting
	if (!worker || !registration.active || !navigator.serviceWorker?.controller) return
	const id = await askBuildId(worker)
	if (registration.waiting !== worker) return
	waitingId = id
	if (!shouldOfferUpdate(id, remembered())) {
		console.info("[update] a build is waiting, and this one was already put away", id)
		return
	}
	console.info("[update] a new build is waiting", id)
	needRefresh.value = true
}

//: One registration, made by main.js and shared (data/swRegistration.js). The
//: prompt used to register the worker a second time under another URL, and the
//: two replaced each other on every load (owner, 28 Sep 2026).
function watchRegistration(registration) {
	if (!registration) return
	consider(registration)
	registration.addEventListener("updatefound", () => {
		const worker = registration.installing
		worker?.addEventListener("statechange", () => {
			if (worker.state === "installed") consider(registration)
		})
	})
}

watch(swRegistration, watchRegistration, { immediate: true })

function dismiss() {
	// Hides the offer, does not decline the build. The worker stays waiting and
	// activates on the next cold start; nothing is lost by putting it away.
	console.info("[update] the employee put the offer away; it will apply on the next load")
	remember(waitingId)
	needRefresh.value = false
}

let reloading = false
function reload() {
	if (reloading) return
	reloading = true
	// Always ends in a reload. Tell the waiting build to take over, reload on
	// controllerchange, and reload anyway after RELOAD_FALLBACK_MS. A reload on
	// the old build is harmless: the waiting one takes over on the next load.
	//
	// The remembered dismissal is cleared first. It belongs to a build that is
	// about to become the CURRENT one.
	try {
		localStorage.removeItem(UPDATE_DISMISS_KEY)
	} catch {
		// Storage being unavailable cannot stop a reload the employee asked for.
	}
	needRefresh.value = false
	console.info("[update] reloading into the new build")
	let reloaded = false
	let fallback = null
	const once = () => {
		clearTimeout(fallback)
		if (reloaded) return
		reloaded = true
		window.location.reload()
	}
	navigator.serviceWorker?.addEventListener("controllerchange", once, { once: true })
	swRegistration.value?.waiting?.postMessage({ type: "SKIP_WAITING" })
	fallback = setTimeout(() => {
		// The new build did not take over. Remember this one as offered, so the
		// next load does not ask again for a build that cannot activate (review
		// of 1526e13bb); a newer build is a new id and is offered normally.
		console.info("[update] no takeover signal; reloading anyway")
		remember(waitingId)
		once()
	}, RELOAD_FALLBACK_MS)
}
</script>
