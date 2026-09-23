<!--
  GDatePicker — date field (spec §10.3 treatment list).

  DECISION (alpha.5): a native <input type="date"> in the Glass input skin.
  It used to skin frappe-ui's DatePicker, which still showed the old grey box
  ("Select From Date") on the owner's New Leave Application screenshot. The
  platform picker is the Apple HIG answer on phones — the iOS/Android date
  wheel, locale-aware, accessible, no popover to fight Ionic's focus trap.
  GCalendar stays a separate DISPLAY component (§10.2 #18), as before.

  Props (unchanged, so callers did not move):
    modelValue  string — ISO date "YYYY-MM-DD"
    label       string — visible field label
    placeholder string — native date inputs draw their own blank; kept for API
                parity and forwarded as the accessible description only
    disabled    boolean
    minDate / maxDate  string — ISO dates, forwarded to min/max
  Emits: update:modelValue ("YYYY-MM-DD", or "" when cleared)
-->
<template>
	<label class="g-field g-datefield">
		<span v-if="label" class="g-field__label">{{ label }}</span>
		<input
			type="date"
			class="g-input g-focusable"
			:value="toDateInput(modelValue)"
			:min="minDate || undefined"
			:max="maxDate || undefined"
			:disabled="disabled"
			:aria-label="!label ? ariaLabel || placeholder || undefined : undefined"
			@change="$emit('update:modelValue', $event.target.value)"
		/>
	</label>
</template>

<script setup>
import { toDateInput } from "@/utils/datetimeInput"

defineProps({
	modelValue: { type: String, default: "" },
	label: { type: String, default: "" },
	ariaLabel: { type: String, default: "" },
	placeholder: { type: String, default: "" },
	disabled: { type: Boolean, default: false },
	minDate: { type: String, default: "" },
	maxDate: { type: String, default: "" },
})
defineEmits(["update:modelValue"])
</script>
