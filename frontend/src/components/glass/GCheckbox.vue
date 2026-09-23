<!--
  GCheckbox — a yes/no tick (Frappe Check fields).

  A native checkbox inside a <label> row: the whole row is the 44px target
  (§14.1), so two stacked checkboxes cannot share a tap area. The label text
  sits beside the box and is always visible.

  Frappe sends Check values as 0/1, the app's own state often as booleans.
  The emitted value keeps the type that came in — 0/1 in, 0/1 out — so a
  form never sees its field flip from 1 to true and turn dirty.

  Props:
    modelValue  boolean | 0 | 1
    label       string
    disabled    boolean
  Emits: update:modelValue, change (same value)
-->
<template>
	<label class="g-check" :class="{ 'g-check--disabled': disabled }">
		<input
			type="checkbox"
			class="g-check__box g-focusable"
			:checked="Boolean(Number(modelValue))"
			:disabled="disabled"
			@change="onChange"
		/>
		<span v-if="label" class="g-check__label">{{ label }}</span>
	</label>
</template>

<script setup>
import { toggleValue } from "@/utils/toggleValue"

const props = defineProps({
	modelValue: { type: [Boolean, Number], default: false },
	label: { type: String, default: "" },
	disabled: { type: Boolean, default: false },
})
const emit = defineEmits(["update:modelValue", "change"])

function onChange(event) {
	const value = toggleValue(props.modelValue, event.target.checked)
	emit("update:modelValue", value)
	emit("change", value)
}
</script>
