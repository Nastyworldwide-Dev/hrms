<!--
  GMapPanel — check-in location panel (spec §10.2 #19): 150px, radius-action
  19px, themed gradient + perspective grid, pin --brand with rings, geo caption
  mono 10px in a glass chip.
  Identical at both breakpoints (§20.7).

  SURFACE ACCOUNTING: the panel body is a GRADIENT, not glass — which is what
  lets the caption chip be glass without nesting (§15 forbids nested glass).
  The panel therefore costs exactly one surface, spent on the chip.

  The pin rings animate transform + opacity only (§8, §15) and stop under
  prefers-reduced-motion, leaving the pin itself visible.

  Slot: default — a real map. Omitted, the decorative placeholder renders.

  Props:
    caption   string — geo caption, e.g. "3.1390° N, 101.6869° E"
    label     string, default "Check-in location" — accessible name; the map is
              decorative to assistive tech, the caption carries the information
    rings     boolean, default true — pulse rings around the pin
    loading   boolean — §11.2 skeleton, no spinner
-->
<template>
	<GSkeleton v-if="loading" height="150px" radius="var(--g-radius-action)" />

	<div v-else class="g-map" :role="$slots.default ? undefined : 'img'" :aria-label="$slots.default ? undefined : label">
		<!-- The gradient, grid and pin are the PLACEHOLDER. A real map goes in
		     the slot and keeps the panel's 150px frame, radius and caption chip. -->
		<slot>
			<span class="g-map__grid" aria-hidden="true" />
			<span class="g-map__pin" aria-hidden="true">
				<template v-if="rings">
					<span class="g-map__ring" />
					<span class="g-map__ring" />
				</template>
			</span>
		</slot>
		<span v-if="caption" class="g-glass g-map__caption">{{ caption }}</span>
	</div>
</template>

<script setup>
import GSkeleton from "./GSkeleton.vue"

defineProps({
	caption: { type: String, default: "" },
	label: { type: String, default: "Check-in location" },
	rings: { type: Boolean, default: true },
	loading: { type: Boolean, default: false },
})
</script>
