<!--
  GSwitch — an on/off setting that takes effect at once (Apple HIG switch).

  A native <button role="switch" aria-checked>: focusable, Space/Enter toggle
  it, and screen readers announce "switch, on/off". The button is the full
  44px target (§14.1); the track drawn inside it is smaller. Use GCheckbox for
  a form answer that is saved later, GSwitch for a live setting.

  Same value rule as GCheckbox: 0/1 in, 0/1 out; boolean in, boolean out.

  Props:
    modelValue  boolean | 0 | 1
    label       string — visible text beside the track; also its name
    ariaLabel   string — name when the label is rendered elsewhere
    disabled    boolean
  Emits: update:modelValue, change (same value)
-->
<template>
	<button
		type="button"
		role="switch"
		class="g-switch g-focusable"
		:class="{ 'g-switch--on': on }"
		:aria-checked="on ? 'true' : 'false'"
		:aria-label="!label && ariaLabel ? ariaLabel : undefined"
		:disabled="disabled"
		@click="flip"
	>
		<span class="g-switch__track" aria-hidden="true">
			<span class="g-switch__thumb" />
		</span>
		<span v-if="label" class="g-switch__label">{{ label }}</span>
	</button>
</template>

<script setup>
import { computed } from "vue"

import { toggleValue } from "@/utils/toggleValue"

const props = defineProps({
	modelValue: { type: [Boolean, Number], default: false },
	label: { type: String, default: "" },
	ariaLabel: { type: String, default: "" },
	disabled: { type: Boolean, default: false },
})
const emit = defineEmits(["update:modelValue", "change"])

const on = computed(() => Boolean(Number(props.modelValue)))

function flip() {
	const value = toggleValue(props.modelValue, !on.value)
	emit("update:modelValue", value)
	emit("change", value)
}
</script>
