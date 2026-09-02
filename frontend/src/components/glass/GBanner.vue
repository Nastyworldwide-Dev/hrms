<!--
  GBanner — banner (spec §10.1 #10): glass surface, radius-banner, 3px left
  rule. Message copy per §11.3 — plain language, no system vocabulary.
  Identical at both breakpoints (§20.7).
  Props:
    variant      "info" | "warning" | "error" — rule colour --brand/--warn/--danger
                 (fills and rules use the constants in both themes, §2.3)
    interactive  boolean — the whole banner is the affordance. Renders a real
                 <button> (keyboard-operable, WCAG 2.1.1) and emits click on
                 activation. Pair with .g-banner--tappable / .g-approvals for
                 the block layout + focus ring. Default false: a passive
                 <div> live region.
  Slot: default — banner content.
  A11y: a passive error announces assertively (role=alert), info/warning
  politely; an interactive banner is a button and describes itself by its copy.
-->
<template>
	<GTag
		:as="interactive ? 'button' : 'div'"
		:type="interactive ? 'button' : undefined"
		class="g-glass g-banner"
		:class="{
			'g-banner--warning': variant === 'warning',
			'g-banner--error': variant === 'error',
		}"
		:role="interactive ? undefined : variant === 'error' ? 'alert' : 'status'"
		@click="interactive && $emit('click', $event)"
	>
		<slot />
	</GTag>
</template>

<script setup>
import GTag from "./GTag.js"

defineProps({
	variant: {
		type: String,
		default: "info",
		validator: (v) => ["info", "warning", "error"].includes(v),
	},
	interactive: {
		type: Boolean,
		default: false,
	},
})

defineEmits(["click"])
</script>
