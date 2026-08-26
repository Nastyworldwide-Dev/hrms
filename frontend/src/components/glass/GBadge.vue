<!--
  GBadge — issue badge (spec §10.1 #7). OPEN: brand fill + on-brand (light),
  brand-18% tint + brand text (dark). RESOLVED: success-ink on success-20%
  (one rule — --success-ink resolves to --success on dark).
  Identical at both breakpoints (§20.7).
  Props:
    variant  "open" | "resolved" | "accent" | "neutral" (required)
             accent/neutral are LABEL chips (a grade, a category, a count) —
             not statuses. A status belongs in GStatusChip.
  Slot: default — the badge text (e.g. OPEN). Text is the accessible name.
-->
<template>
	<span class="g-badge" :class="variantClass">
		<slot />
	</span>
</template>

<script setup>
import { computed } from "vue"

// accent/neutral reuse the GStatusChip variant treatments rather than
// duplicating them — same measured pairs, one definition
const VARIANTS = {
	open: "g-badge--open",
	resolved: "g-badge--resolved",
	accent: "g-chip--progress",
	neutral: "g-chip--neutral",
}

const props = defineProps({
	variant: {
		type: String,
		required: true,
		validator: (v) => ["open", "resolved", "accent", "neutral"].includes(v),
	},
})

const variantClass = computed(() => VARIANTS[props.variant])
</script>
