<!--
  GDateTimePicker — datetime field. Same decision as GDatePicker: a native
  <input type="datetime-local"
			step="1"> in the Glass input skin, so phones show their
  own date-and-time wheel (Apple HIG) instead of frappe-ui's grey popover.

  The only work here is the format: Frappe stores "YYYY-MM-DD HH:mm:ss", the
  native input speaks "YYYY-MM-DDTHH:mm" — utils/datetimeInput converts both
  ways (and is where the round-trip tests live).

  Props (unchanged, so callers did not move):
    modelValue  string — "YYYY-MM-DD HH:mm:ss"
    label       string — visible field label
    placeholder string — kept for API parity; used as the accessible name
                only when there is no label
    disabled    boolean
  Emits: update:modelValue ("YYYY-MM-DD HH:mm:ss", or "" when cleared)
-->
<template>
	<label class="g-field g-datefield">
		<span v-if="label" class="g-field__label">{{ label }}</span>
		<input
			type="datetime-local"
			class="g-input g-focusable"
			:value="toDatetimeLocal(modelValue)"
			:disabled="disabled"
			:aria-label="!label ? ariaLabel || placeholder || undefined : undefined"
			@change="$emit('update:modelValue', fromDatetimeLocal($event.target.value))"
		/>
	</label>
</template>

<script setup>
import { fromDatetimeLocal, toDatetimeLocal } from "@/utils/datetimeInput"

defineProps({
	modelValue: { type: String, default: "" },
	label: { type: String, default: "" },
	ariaLabel: { type: String, default: "" },
	placeholder: { type: String, default: "" },
	disabled: { type: Boolean, default: false },
})
defineEmits(["update:modelValue"])
</script>
