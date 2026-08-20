<!--
  GButton — primary action (spec §10.1 #1; states §11.4; no shimmer sweep §7).
  Identical at both breakpoints (§20.7).
  Props:
    label        string, required — button text, also the accessible name
    pendingLabel string — progressive form shown while pending ("Sending…");
                 falls back to label
    pending      boolean — §11.4: keeps brand fill, swaps label, 2px
                 transform-animated bar on the bottom edge, aria-busy
    disabled     boolean — §11.4: icon-bg fill, ink3 label, aria-disabled;
                 stays focusable so the state is discoverable
  Emits: click — suppressed while pending or disabled (§11.5 duplicate guard
         is the caller's 60s window; this only stops re-entry while pending)
-->
<template>
	<button
		type="button"
		class="g-btn"
		:class="{ 'g-btn--pending': pending, 'g-btn--disabled': disabled }"
		:aria-busy="pending || undefined"
		:aria-disabled="disabled || undefined"
		@click="onClick"
	>
		<span>{{ pending ? pendingLabel || label : label }}</span>
		<span v-if="pending" class="g-btn__bar" aria-hidden="true" />
	</button>
</template>

<script setup>
const props = defineProps({
	label: { type: String, required: true },
	pendingLabel: { type: String, default: "" },
	pending: { type: Boolean, default: false },
	disabled: { type: Boolean, default: false },
})
const emit = defineEmits(["click"])

function onClick(event) {
	if (props.pending || props.disabled) return
	emit("click", event)
}
</script>
