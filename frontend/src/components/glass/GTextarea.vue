<!--
  GTextarea — GInput variant (spec §10.1 #5): height 66px, align-items
  flex-start. Same tokens, focus ring and error behaviour as GInput.
  Identical at both breakpoints (§20.7).

  Props: modelValue, label, placeholder, error, disabled — see GInput.
  Emits: update:modelValue
-->
<template>
	<label class="g-field">
		<span v-if="label" class="g-field__label">{{ label }}</span>
		<textarea
			class="g-input g-input--textarea"
			:class="{ 'g-input--error': error }"
			:value="modelValue"
			:placeholder="placeholder"
			:disabled="disabled"
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
	modelValue: { type: String, default: "" },
	label: { type: String, default: "" },
	placeholder: { type: String, default: "" },
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
