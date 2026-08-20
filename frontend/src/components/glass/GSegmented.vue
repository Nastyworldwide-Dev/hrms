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
	<div class="g-seg" role="tablist" :aria-label="label">
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

<style scoped>
/* 38px visual + 3px track padding either side = the 44px target (§5) */
.g-seg__option {
	min-height: 38px;
}
</style>
