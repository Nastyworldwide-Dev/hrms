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

  Props:
    pullingText     string, default "Pull to refresh"
    refreshingText  string, default "Refreshing…"
  Emits: refresh(event) — pass the event to complete(): event.target.complete()
-->
<template>
	<ion-refresher
		slot="fixed"
		pulling-icon="none"
		:refreshing-spinner="null"
		@ionRefresh="onRefresh"
		@ionStart="onStart"
	>
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
import { onBeforeUnmount, ref } from "vue"
import { IonRefresher, IonRefresherContent } from "@ionic/vue"

defineProps({
	pullingText: { type: String, default: "Pull to refresh" },
	refreshingText: { type: String, default: "Refreshing…" },
})
const emit = defineEmits(["refresh"])

const refreshing = ref(false)
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

onBeforeUnmount(() => clearTimeout(capTimer))
</script>
