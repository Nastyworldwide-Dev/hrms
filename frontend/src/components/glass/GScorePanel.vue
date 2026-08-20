<!--
  GScorePanel — KPI score panel (spec §10.2 #15): GProgressRing + verdict +
  cycle pill, pad 17px 15px, radius-panel 20px.
  ONE glass surface — the ring inside is an SVG, not a surface (§15).
  Identical at both breakpoints (§20.7).

  Props:
    score    number, required — passed to GProgressRing
    max      number, default 5
    verdict  string, required — e.g. "Exceeds expectations"
    cycle    string — cycle pill, e.g. "H1 2026 REVIEW"
    loading  boolean — §11.2 skeletons, no spinner
-->
<template>
	<div class="g-glass g-score">
		<GProgressRing :score="score" :max="max" :loading="loading" />
		<div>
			<template v-if="loading">
				<GSkeleton width="120px" height="15px" />
				<GSkeleton width="86px" height="11px" />
			</template>
			<template v-else>
				<div class="g-score__verdict">{{ verdict }}</div>
				<div v-if="cycle" class="g-score__pill">{{ cycle }}</div>
			</template>
		</div>
	</div>
</template>

<script setup>
import GProgressRing from "./GProgressRing.vue"
import GSkeleton from "./GSkeleton.vue"

defineProps({
	score: { type: Number, required: true },
	max: { type: Number, default: 5 },
	verdict: { type: String, required: true },
	cycle: { type: String, default: "" },
	loading: { type: Boolean, default: false },
})
</script>

<style scoped>
:deep(.g-skeleton) + :deep(.g-skeleton) {
	margin-top: 8px;
}
</style>
