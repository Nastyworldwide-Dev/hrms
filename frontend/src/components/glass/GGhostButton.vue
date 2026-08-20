<!--
  GGhostButton — ghost action (spec §10.1 #2): glass at --blur-ghost, --ink
  label. A glass surface — counts against the §15 budget via .g-glass-ghost.
  Identical at both breakpoints (§20.7).
  Props:
    label    string, required — button text, also the accessible name
    disabled boolean — §11.4 disabled treatment, aria-disabled
  Emits: click — suppressed while disabled
-->
<template>
	<button
		type="button"
		class="g-glass-ghost g-ghost-btn"
		:class="{ 'g-btn--disabled': disabled }"
		:aria-disabled="disabled || undefined"
		@click="onClick"
	>
		{{ label }}
	</button>
</template>

<script setup>
const props = defineProps({
	label: { type: String, required: true },
	disabled: { type: Boolean, default: false },
})
const emit = defineEmits(["click"])

function onClick(event) {
	if (props.disabled) return
	emit("click", event)
}
</script>
