<!--
  GMetaGrid — read-only key/value facts on ONE glass surface (spec §15.2).

  The shape a screen reaches for when it has to state four short facts about
  the thing being looked at: who raised a ticket, its reference, its priority,
  its agent. Four rows in a list panel is 4 x 56px of screen for eight words;
  a 2-up cell grid is half that and reads in one glance.

  THE SURFACE BOUNDARY, same as GListPanel and GStatPanel: this component
  carries .g-glass, its cells do not. Container + N cells = ONE surface against
  the §15 budget of 6. TicketDetail built this by hand and so held .g-glass in
  a view, which views are not allowed to do — a hand-built panel is a panel
  that drifts from the system the next time the system moves.

  Dividers are drawn as cell borders so the panel keeps one background. An odd
  final cell spans the full width rather than sitting beside an empty,
  half-bordered gap — the same rule GBalanceGrid already applies.

  Props:
    cells    Array<{ k: string, v: string | number }>, required
    loading  boolean — §11.2 skeleton cells, never a spinner
-->
<template>
	<div class="g-glass g-cellgrid g-cellgrid--meta" :class="{ 'g-cellgrid--odd': isOdd }">
		<template v-if="loading">
			<div v-for="n in 4" :key="n" class="g-cell g-cell--meta" aria-hidden="true">
				<GSkeleton width="42%" height="10px" />
				<GSkeleton width="72%" height="13px" />
			</div>
		</template>
		<div v-for="cell in cells" v-else :key="cell.k" class="g-cell g-cell--meta">
			<span class="g-eyebrow">{{ cell.k }}</span>
			<span class="g-meta__value">{{ cell.v }}</span>
		</div>
	</div>
</template>

<script setup>
import { computed } from "vue"

import GSkeleton from "./GSkeleton.vue"

const props = defineProps({
	cells: { type: Array, required: true },
	loading: { type: Boolean, default: false },
})

const isOdd = computed(() => !props.loading && props.cells.length % 2 === 1)
</script>

<style scoped>
.g-cell--meta > :deep(.g-skeleton) + :deep(.g-skeleton) {
	margin-top: 6px;
}
</style>
