<!--
  GSegmented — segmented control (spec §10.3, "also requiring a treatment").
  Not a surface; it sits on one. Identical at both breakpoints (§20.7).

  API MATCHES the existing TabButtons.vue exactly, so phase 5 can swap the
  import without touching call sites:
    props   buttons: Array, modelValue: String
    emits   update:modelValue
    key     button.key ?? button.label ?? button
    label   button.label ?? __(button)
  TabButtons.vue itself is NOT modified.

  Options are 44px touch targets (§5) and carry the two-tone focus ring
  (§14.3). Selection is announced via role=tab/aria-selected, so it is never
  carried by colour alone (§14.1).

  Props:
    buttons     array, required — strings or { key, label }
    modelValue  string — the selected key
    label       string, default "View" — accessible name for the tablist
  Emits: update:modelValue
-->
<template>
	<!-- A ONE-OPTION CONTROL IS NOT A CONTROL (8.8). For a non-approver
	     RequestPanel passes a single tab, and the strip rendered one full-width
	     accent-filled segment — indistinguishable from a primary action, and
	     the thing a reviewer read as "a section header styled as a button".
	     With nothing to switch to there is nothing to render. -->
	<div v-if="buttons.length > 1" class="g-seg" role="tablist" :aria-label="label">
		<button
			v-for="button in buttons"
			:key="keyOf(button)"
			type="button"
			role="tab"
			class="g-seg__option g-focusable"
			:class="{ 'g-seg__option--selected': modelValue === keyOf(button) }"
			:aria-selected="modelValue === keyOf(button)"
			@click="$emit('update:modelValue', keyOf(button))"
		>
			{{ button.label ?? t(button) }}
		</button>
	</div>
</template>

<script setup>
import { useTranslate } from "./translate"

defineProps({
	buttons: { type: Array, required: true },
	modelValue: { type: String, default: "" },
	label: { type: String, default: "View" },
})
defineEmits(["update:modelValue"])

const t = useTranslate()

// identical resolution order to TabButtons.vue
function keyOf(button) {
	return button.key ?? button.label ?? button
}
</script>

<!-- No scoped style. This block held `min-height: 38px` with the note
     "38px visual + 3px track padding either side = the 44px target (§5)" —
     but the track's padding is not part of the option's box: a tap 2px above
     an option lands on the track, so the real target was 38px, and being
     scoped it silently outranked the theme layer's own rule by data-v
     specificity. §14.1 lives in theme/glass-components.css. -->
