<!--
  GBadge — issue badge (spec §10.1 #7). OPEN: brand fill + on-brand (light),
  brand-18% tint + brand text (dark). RESOLVED: success-ink on success-20%
  (one rule — --success-ink resolves to --success on dark).
  Identical at both breakpoints (§20.7).
  Props:
    variant  "open" | "resolved" (required)
  Slot: default — the badge text (e.g. OPEN). Text is the accessible name.
-->
<template>
	<span class="g-badge" :class="`g-badge--${variant}`">
		<slot />
	</span>
</template>

<script setup>
defineProps({
	variant: {
		type: String,
		required: true,
		validator: (v) => ["open", "resolved"].includes(v),
	},
})
</script>
