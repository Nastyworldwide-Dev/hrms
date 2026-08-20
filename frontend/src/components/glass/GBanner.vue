<!--
  GBanner — banner (spec §10.1 #10): glass surface, radius-banner, 3px left
  rule. Message copy per §11.3 — plain language, no system vocabulary.
  Identical at both breakpoints (§20.7).
  Props:
    variant  "info" | "warning" | "error" — rule colour --brand/--warn/--danger
             (fills and rules use the constants in both themes, §2.3)
  Slot: default — banner content.
  A11y: error announces assertively (role=alert), info/warning politely.
-->
<template>
	<div
		class="g-glass g-banner"
		:class="{
			'g-banner--warning': variant === 'warning',
			'g-banner--error': variant === 'error',
		}"
		:role="variant === 'error' ? 'alert' : 'status'"
	>
		<slot />
	</div>
</template>

<script setup>
defineProps({
	variant: {
		type: String,
		default: "info",
		validator: (v) => ["info", "warning", "error"].includes(v),
	},
})
</script>
