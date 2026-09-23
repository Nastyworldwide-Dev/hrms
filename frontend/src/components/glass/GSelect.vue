<!--
  GSelect — choose one of a fixed list (Frappe Select fields).

  A native <select> in the Glass input skin. On phones the OS draws its own
  wheel/list (Apple HIG: use the platform picker), keyboard and screen readers
  get the real control for free, and there is no popover to fight Ionic's
  focus trap. 44px tall (§14.1), two-tone focus ring via .g-focusable.

  Props:
    modelValue  string | number — v-model; "" means nothing chosen
    options     array — [{ label, value }]
    label       string — visible label (always shown when given)
    ariaLabel   string — accessible name when the caller renders the label
    placeholder string — the empty first option; plain words, never "Select X"
    disabled    boolean
  Emits: update:modelValue (the option's value, or "" for the empty option)
-->
<template>
	<label class="g-field">
		<span v-if="label" class="g-field__label">{{ label }}</span>
		<span class="g-select">
			<select
				class="g-input g-select__native g-focusable"
				:class="{ 'g-select--empty': modelValue === '' || modelValue == null }"
				:value="modelValue ?? ''"
				:disabled="disabled"
				:aria-label="!label && ariaLabel ? ariaLabel : undefined"
				@change="$emit('update:modelValue', $event.target.value)"
			>
				<option value="">{{ placeholder }}</option>
				<option
					v-for="option in options"
					:key="String(option.value)"
					:value="option.value"
				>
					{{ option.label ?? option.value }}
				</option>
			</select>
			<ChevronDown class="g-select__chevron" aria-hidden="true" />
		</span>
	</label>
</template>

<script setup>
import { ChevronDown } from "lucide-vue-next"

defineProps({
	modelValue: { type: [String, Number], default: "" },
	options: { type: Array, default: () => [] },
	label: { type: String, default: "" },
	ariaLabel: { type: String, default: "" },
	placeholder: { type: String, default: "" },
	disabled: { type: Boolean, default: false },
})
defineEmits(["update:modelValue"])
</script>
