<!--
  GDateTimePicker — datetime field. Same decision as GDatePicker (skins
  frappe-ui's real picker rather than hand-rolling one): frappe-ui's
  DateTimePicker shares DatePicker's prop/emit shape (see its own source —
  it imports DatePickerProps/DatePickerEmits directly), so this is the same
  wrapper with a different import.

  Props:
    modelValue  string — "YYYY-MM-DD HH:mm:ss"
    label       string — field label, uppercase like GInput's
    placeholder string
    disabled    boolean — forwarded as `readonly` (see GDatePicker's note)
  Emits: update:modelValue
-->
<template>
	<div class="g-field g-datefield">
		<span v-if="label" class="g-field__label">{{ label }}</span>
		<DateTimePicker
			:model-value="modelValue"
			:placeholder="placeholder"
			:readonly="disabled"
			@update:model-value="$emit('update:modelValue', $event)"
		/>
	</div>
</template>

<script setup>
import { DateTimePicker } from "frappe-ui"

defineProps({
	modelValue: { type: String, default: "" },
	label: { type: String, default: "" },
	placeholder: { type: String, default: "" },
	disabled: { type: Boolean, default: false },
})
defineEmits(["update:modelValue"])
</script>
