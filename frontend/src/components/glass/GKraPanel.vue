<!--
  GKraPanel — KRA rows (spec §10.2 #16): rows pad 11px 0, --hair divider,
  label 11.5/600 + mono weight, score display, 4px bar.
  ONE glass surface; rows are not surfaces (§15.1).
  Identical at both breakpoints (§20.7).

  Bar track is --track-solid, NOT --icon-bg: §6.3 names KRA bars explicitly —
  a score a person may dispute with their manager may not be read through a
  moving tint.

  Score size: §10.2 #16 says 13/800; §4.2's scale has no 13px step, so the
  nearest (card-title 12.5px) carries the size and the display weight carries
  the 800. Flagged for a §4.2 ruling.

  Props:
    rows     array, required — [{ label, weight, score, max }]
             weight is the KRA weightage string (e.g. "30%"), rendered mono
    loading  boolean — §11.2 skeleton rows, no spinner
    skeletonRows number, default 4
-->
<template>
	<div class="g-glass g-kra">
		<template v-if="loading">
			<div v-for="n in skeletonRows" :key="n" class="g-kra__row" aria-hidden="true">
				<div class="g-kra__top">
					<GSkeleton width="46%" height="11px" />
					<GSkeleton width="28px" height="11px" />
				</div>
				<GSkeleton height="4px" radius="var(--g-radius-pill)" />
			</div>
		</template>

		<template v-else>
			<div v-for="row in rows" :key="row.label" class="g-kra__row">
				<div class="g-kra__top">
					<span class="g-kra__label">{{ row.label }}</span>
					<span class="g-kra__weight">{{ row.weight }}</span>
					<span class="g-kra__score">{{ row.score }}</span>
				</div>
				<div
					class="g-kra__bar"
					role="img"
					:aria-label="`${row.label}, ${row.score} out of ${row.max ?? 5}`"
				>
					<div class="g-kra__fill" :style="{ width: `${fill(row)}%` }" />
				</div>
			</div>
		</template>
	</div>
</template>

<script setup>
import GSkeleton from "./GSkeleton.vue"

defineProps({
	rows: { type: Array, default: () => [] },
	loading: { type: Boolean, default: false },
	skeletonRows: { type: Number, default: 4 },
})

// clamped like GProgressRing: an out-of-range score must not overrun the track
function fill(row) {
	const max = row.max ?? 5
	if (!max) return 0
	return Math.min(100, Math.max(0, (row.score / max) * 100))
}
</script>

<style scoped>
.g-kra__row :deep(.g-skeleton) + :deep(.g-skeleton) {
	margin-top: 7px;
}
</style>
