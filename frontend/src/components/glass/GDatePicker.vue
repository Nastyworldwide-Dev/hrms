<!--
  GDatePicker — date field (spec §10.3 treatment list).

  DECISION: skins frappe-ui's **DatePicker**; does NOT build on GCalendar.

  Two reasons. First, GCalendar is an attendance DISPLAY — a month grid whose
  cells carry present/leave/rest state colours and a legend (§10.2 #18). A
  picker needs selection, month navigation, keyboard traversal, parsing and
  range handling; bolting those onto a display component produces one component
  doing two jobs badly, and every §10.2 #18 change would then risk the date
  fields. Second, DatePicker ships in the installed 0.1.105 (unlike Combobox —
  see GLinkPicker), so this costs a skin rather than a date library.

  GCalendar and GDatePicker therefore stay separate on purpose: same month-grid
  shape, different jobs.

  Props:
    modelValue  string — ISO date
    label       string — field label, uppercase like GInput's
    placeholder string
    disabled    boolean — forwarded as frappe-ui DatePicker's `readonly`
                (its real prop; it has no `disabled`, and `readonly` is what
                actually gates the popover open — see its @focus handler).
                Kept as `disabled` here so every G* form field shares one
                name for "can't edit this."
  Emits: update:modelValue
-->
<template>
	<div class="g-field g-datefield">
		<span v-if="label" class="g-field__label">{{ label }}</span>
		<DatePicker
			:model-value="modelValue"
			:placeholder="placeholder"
			:readonly="disabled"
			@update:model-value="$emit('update:modelValue', $event)"
		/>
	</div>
</template>

<script setup>
import { DatePicker } from "frappe-ui"

defineProps({
	modelValue: { type: String, default: "" },
	label: { type: String, default: "" },
	placeholder: { type: String, default: "" },
	disabled: { type: Boolean, default: false },
})
defineEmits(["update:modelValue"])
</script>
