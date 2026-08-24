<!--
  GLinkPicker — Frappe link field (spec §10.3 treatment list).

  DECISION: wraps frappe-ui's **Autocomplete**, not Combobox.
  Combobox does not exist in the installed frappe-ui (0.1.105) — it arrives in
  0.1.278, and taking it means taking the whole upgrade, which is unresolved
  DECISION 6 (§16.1). Autocomplete ships in 0.1.105, and both
  ListFiltersActionSheet.vue and RequestActionSheet.vue already use it, so
  wrapping keeps one link-field behaviour in the app instead of two. Revisit
  when DECISION 6 lands.

  Wrapped rather than rebuilt: the value here is Frappe's link semantics —
  remote search, debouncing, doctype filtering, keyboard selection. None of
  that is design, and rebuilding it to change colours would be a poor trade.

  The Glass skin reaches Autocomplete's popover because it renders as plain
  DOM, not shadow DOM. It IS coupled to frappe-ui's internal markup — re-verify
  on the 0.1.278 upgrade.

  Props (Autocomplete's, passed straight through):
    modelValue  object | string
    options     array — [{ label, value }]
    placeholder string
    label       string — field label, uppercase like GInput's
    disabled    boolean
  Emits: update:modelValue
-->
<template>
	<div class="g-field g-linkfield">
		<span v-if="label" class="g-field__label">{{ label }}</span>
		<Autocomplete
			:model-value="modelValue"
			:options="options"
			:placeholder="placeholder"
			:disabled="disabled"
			@update:model-value="$emit('update:modelValue', $event)"
		/>
	</div>
</template>

<script setup>
import { Autocomplete } from "frappe-ui"

defineProps({
	modelValue: { type: [Object, String], default: null },
	options: { type: Array, default: () => [] },
	placeholder: { type: String, default: "" },
	label: { type: String, default: "" },
	disabled: { type: Boolean, default: false },
})
defineEmits(["update:modelValue"])
</script>
