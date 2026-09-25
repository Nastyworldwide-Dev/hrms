<!--
  GInput — form field (spec §10.1 #4). Not a glass surface; it sits on one.
  pad 13px 14px, radius-input 14px, 12.5px text, placeholder --ink-muted,
  filled --ink. Two-tone focus ring (§14.3). Min-height 44px (§14.1).
  Identical at both breakpoints (§20.7).

  Error state uses --danger-ink, whose dark value is --danger itself — so the
  one token satisfies the spec's "danger-ink on light, danger on dark" rule.

  Props:
    modelValue  string | number — v-model
    label       string — field label, uppercase; also the accessible name
    ariaLabel   string — accessible name for a caller that renders its OWN
                visible label elsewhere (FormField.vue's field label is a
                sibling <span>, not a <label for>, so it associates with
                nothing without this — see the Time field, §14 a11y audit)
    placeholder string
    type        string, default "text"
    error       string — message shown below; also flips the border and sets
                aria-invalid. Empty string = no error (§11.3 copy rules apply)
    disabled    boolean
  Emits: update:modelValue
-->
<template>
	<label class="g-field">
		<span v-if="label" class="g-field__label">{{ label }}</span>
		<input
			class="g-input"
			:class="{ 'g-input--error': error }"
			:type="type"
			:value="modelValue"
			:placeholder="placeholder"
			:min="min || undefined"
			:max="max || undefined"
			:disabled="disabled"
			:aria-label="!label && ariaLabel ? ariaLabel : undefined"
			:aria-invalid="error ? 'true' : undefined"
			:aria-describedby="error ? errorId : undefined"
			:aria-disabled="disabled || undefined"
			@input="$emit('update:modelValue', $event.target.value)"
		/>
		<span v-if="error" :id="errorId" class="g-field__error" role="alert">{{ error }}</span>
	</label>
</template>

<script setup>
import { useId } from "vue"

defineProps({
	modelValue: { type: [String, Number], default: "" },
	label: { type: String, default: "" },
	ariaLabel: { type: String, default: "" },
	placeholder: { type: String, default: "" },
	type: { type: String, default: "text" },
	//: Bounds for a date / time / number input, on the input itself.
	min: { type: String, default: "" },
	max: { type: String, default: "" },
	error: { type: String, default: "" },
	disabled: { type: Boolean, default: false },
})
defineEmits(["update:modelValue"])

// Per INSTANCE, not per component: two invalid fields on one form sharing an
// id would mean the second field describes the first field's error. Vue's own
// useId is stable across server and client, so it cannot mismatch on hydration
// the way a random id would.
const errorId = useId()
</script>
