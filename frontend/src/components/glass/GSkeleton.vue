<!--
  GSkeleton — loading block (spec §11.2). Mirrors the real layout: compose one
  per block with the block's real size and radius. Shimmer is transform-only
  and goes static under prefers-reduced-motion. No spinners anywhere (§11.2).
  Identical at both breakpoints (§20.7).
  Props:
    width   CSS length, default "100%"
    height  CSS length, default "14px"
    radius  CSS length, default var(--g-radius-pill) (spec: block r6)
-->
<template>
	<div class="g-skeleton" :style="{ width, height, borderRadius: radius }" aria-hidden="true" />
</template>

<script setup>
defineProps({
	width: { type: String, default: "100%" },
	height: { type: String, default: "14px" },
	radius: { type: String, default: "var(--g-radius-pill)" },
})
</script>
