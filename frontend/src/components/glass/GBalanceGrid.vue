<!--
  GBalanceGrid — the flattened balance panel (spec §15.2, §20.5).

  ONE glass surface with internal --hair dividers, NOT N glass cards. The
  mockup's 2×2 grid of four glass cards cost 4 of the §15 budget of 6; this
  costs 1. Child GBalanceCards are cells and carry no glass.
  §20.5: 2 columns on mobile → 4 columns at lg:, one row, no top dividers.

  Props:
    loading  boolean — §11.2 skeleton cells, no spinner
    cells    number, default 4 — skeleton cell count while loading
    empty    boolean — render the empty slot (§11.1: "No leave allocated yet")
  Slots:
    default  — GBalanceCard children
    empty    — shown when `empty`; use GEmptyState
-->
<template>
	<!-- ONE .g-glass element for every state (§15.2): the empty, loading and
	     filled variants are mutually-exclusive content INSIDE the single
	     surface, not three sibling surfaces. Keeping them as separate top-level
	     .g-glass blocks read as multiple surfaces to a static counter even
	     though only one ever renders. -->
	<div
		class="g-glass"
		:class="empty ? 'g-list' : ['g-cellgrid', 'g-cellgrid--balance', { 'g-cellgrid--odd': !loading && isOdd }]"
		:style="!empty && !loading ? { '--bcols': lgCols } : null"
	>
		<div v-if="empty" class="g-cellgrid__empty">
			<slot name="empty" />
		</div>
		<template v-else-if="loading">
			<div v-for="n in cells" :key="n" class="g-cell" aria-hidden="true">
				<GSkeleton width="52%" height="27px" />
				<GSkeleton height="3px" />
				<GSkeleton width="74%" height="9px" />
			</div>
		</template>
		<slot v-else />
	</div>
</template>

<script setup>
import { computed } from "vue"

import GSkeleton from "./GSkeleton.vue"

const props = defineProps({
	loading: { type: Boolean, default: false },
	cells: { type: Number, default: 4 },
	empty: { type: Boolean, default: false },
	// Number of tiles rendered into the default slot. Drives the odd-count
	// layout so an odd tile count never orphans a cell (see glass-components.css:
	// .g-cellgrid--balance). 0 keeps the legacy fixed layout for callers that
	// pass exactly four and never set it.
	count: { type: Number, default: 0 },
})

// Odd tile count -> the last tile spans the full width on mobile instead of
// leaving an empty bordered cell beside it.
const isOdd = computed(() => props.count % 2 === 1)
// Desktop lays the tiles out in one row of exactly `count` columns (capped) so
// three types fill a row of three, not four-with-a-hole. Capped at 5 so a rare
// many-type employee wraps rather than shrinking tiles to nothing.
const lgCols = computed(() => Math.min(Math.max(props.count, 1), 5))
</script>

<style scoped>
.g-cell > :deep(.g-skeleton) + :deep(.g-skeleton) {
	margin-top: 8px;
}
.g-cellgrid__empty {
	padding: var(--g-pad-panel);
}
</style>
