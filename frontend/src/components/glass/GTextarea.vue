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
			:aria-disabled="disabled || undefined"
			@input="$emit('update:modelValue', $event.target.value)"
		/>
		<span v-if="error" class="g-field__error" role="alert">{{ error }}</span>
	</label>
</template>

<script setup>
defineProps({
	modelValue: { type: String, default: "" },
	label: { type: String, default: "" },
	placeholder: { type: String, default: "" },
	error: { type: String, default: "" },
	disabled: { type: Boolean, default: false },
})
defineEmits(["update:modelValue"])
</script>
