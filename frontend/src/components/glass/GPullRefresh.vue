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
	<ion-refresher slot="fixed" pulling-icon="none" :refreshing-spinner="null" @ionRefresh="onRefresh">
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
import { ref } from "vue"
import { IonRefresher, IonRefresherContent } from "@ionic/vue"

defineProps({
	pullingText: { type: String, default: "Pull to refresh" },
	refreshingText: { type: String, default: "Refreshing…" },
})
const emit = defineEmits(["refresh"])

const refreshing = ref(false)

function onRefresh(event) {
	refreshing.value = true
	console.info("[GPullRefresh] refresh started")
	// the caller completes the gesture; reset once Ionic reports it done
	event.target?.addEventListener?.("ionRefreshComplete", () => (refreshing.value = false), {
		once: true,
	})
	emit("refresh", event)
}
</script>
