<!--
  GSwitch — an on/off setting that takes effect at once (Apple HIG switch).

  alpha.7 B17: Safari's own switch, <input type="checkbox" switch> (Safari
  17.4+): Apple's look, announced as a switch, and on iOS 18 the only haptic
  a web app gets (webkit.org/blog/15054, /15865). Where a browser has no
  native switch (Chrome, older Safari), the same input stays underneath for
  focus and screen readers, and our track is drawn over it (g-switch--drawn).
  The label is the full 44px target.

  Same value rule as GCheckbox: 0/1 in, 0/1 out; boolean in, boolean out.

  Props:
    modelValue  boolean | 0 | 1
    label       string — visible text beside the track; also its name
    ariaLabel   string — name when the label is rendered elsewhere
    disabled    boolean
  Emits: update:modelValue, change (same value)
-->
<template>
	<label class="g-switch" :class="{ 'g-switch--on': on, 'g-switch--drawn': !NATIVE_SWITCH }">
		<input
			type="checkbox"
			switch
			role="switch"
			class="g-switch__input g-focusable"
			:checked="on"
			:aria-label="!label && ariaLabel ? ariaLabel : undefined"
			:disabled="disabled"
			@change="flip"
		/>
		<span v-if="!NATIVE_SWITCH" class="g-switch__track" aria-hidden="true">
			<span class="g-switch__thumb" />
		</span>
		<span v-if="label" class="g-switch__label">{{ label }}</span>
	</label>
</template>

<script setup>
import { computed } from "vue"

import { toggleValue } from "@/utils/toggleValue"

//: Safari 17.4+ exposes the switch attribute on the input prototype.
const NATIVE_SWITCH = typeof HTMLInputElement !== "undefined" && "switch" in HTMLInputElement.prototype

const props = defineProps({
	modelValue: { type: [Boolean, Number], default: false },
	label: { type: String, default: "" },
	ariaLabel: { type: String, default: "" },
	disabled: { type: Boolean, default: false },
})
const emit = defineEmits(["update:modelValue", "change"])

const on = computed(() => Boolean(Number(props.modelValue)))

function flip(event) {
	const value = toggleValue(props.modelValue, event.target.checked)
	emit("update:modelValue", value)
	emit("change", value)
}
</script>
