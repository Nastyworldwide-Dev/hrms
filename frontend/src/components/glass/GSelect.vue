<!--
  GSelect — choose one of a fixed list (Frappe Select fields).

  A native <select> in the Glass input skin. On phones the OS draws its own
  wheel/list (Apple HIG: use the platform picker), keyboard and screen readers
  get the real control for free, and there is no popover to fight Ionic's
  focus trap. 44px tall (§14.1), two-tone focus ring via .g-focusable.

  Props:
    modelValue  string | number — v-model; "" means nothing chosen
    options     array — [{ label, value }], or groups
                [{ group, hideLabel?, items: [{ label, value }] }] drawn as
                <optgroup> (an unlabelled group's items sit at the top level)
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
				<!-- No blank first slot on a select that always has a value (iOS
				     draws it as an empty row above the choices, alpha.7 0.7). -->
				<option v-if="placeholder || modelValue === '' || modelValue == null" value="">{{ placeholder }}</option>
				<template v-for="option in options" :key="option.items ? `g:${option.group}` : String(option.value)">
					<optgroup v-if="option.items && !option.hideLabel" :label="option.group">
						<option v-for="item in option.items" :key="String(item.value)" :value="item.value">
							{{ item.label ?? item.value }}
						</option>
					</optgroup>
					<template v-else-if="option.items">
						<option
							v-for="item in option.items"
							:key="String(item.value)"
							:value="item.value"
							:hidden="item.value === '' || undefined"
						>
							{{ item.label ?? item.value }}
						</option>
					</template>
					<option v-else :value="option.value">
						{{ option.label ?? option.value }}
					</option>
				</template>
			</select>
			<ChevronsUpDown class="g-select__chevron" aria-hidden="true" />
		</span>
	</label>
</template>

<script setup>
import { ChevronsUpDown } from "lucide-vue-next"

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
