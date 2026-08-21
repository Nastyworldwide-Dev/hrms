<!--
  GSelfiePanel — check-in selfie panel (spec §10.2 #20): 118px, radius-action
  19px, 48px dashed --accent-ink ring, 24×24 face icon.
  ONE glass surface. Identical at both breakpoints (§20.7).

  The face icon is drawn on the 24×24 grid — §9's single exception to the
  16-grid, granted for the selfie face.

  Slot: default — populated content, e.g. a live camera preview. Omitted, the
        panel renders the dashed ring placeholder, which is its empty state.

  Props:
    label     string, default "Take your check-in photo" — accessible name
    tappable  boolean, default true — opens the camera; carries the focus ring
    loading   boolean — §11.2 skeleton, no spinner
  Emits: click
-->
<template>
	<GSkeleton v-if="loading" height="118px" radius="var(--g-radius-action)" />

	<GTag
		v-else
		:as="tappable ? 'button' : 'div'"
		:type="tappable ? 'button' : undefined"
		class="g-glass g-selfie"
		:class="{ 'g-focusable': tappable }"
		:aria-label="tappable ? label : undefined"
		@click="tappable && $emit('click', $event)"
	>
		<!-- The dashed ring is the EMPTY state (§11.1). A live camera preview is
		     the populated one, and it goes in the slot — the panel keeps its
		     118px frame and radius either way. -->
		<slot>
			<span class="g-selfie__ring">
				<svg class="g-icon" width="24" height="24" viewBox="0 0 24 24" aria-hidden="true">
					<circle cx="12" cy="9" r="4" />
					<path d="M4.5 20a7.5 7.5 0 0 1 15 0" />
				</svg>
			</span>
		</slot>
	</GTag>
</template>

<script setup>
import GSkeleton from "./GSkeleton.vue"
import GTag from "./GTag.js"

defineProps({
	label: { type: String, default: "Take your check-in photo" },
	tappable: { type: Boolean, default: true },
	loading: { type: Boolean, default: false },
})
defineEmits(["click"])
</script>

<!-- No scoped style for theme-owned classes (8.16). A scoped rule carries a
     [data-v-*] attribute, so it outranks the theme layer — including its
     media queries — and the lint gate cannot see it because it only reads
     theme/glass-components.css. These declarations now live there. -->
