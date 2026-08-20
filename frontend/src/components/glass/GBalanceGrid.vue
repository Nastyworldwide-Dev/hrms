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
	<div v-if="empty" class="g-glass g-list">
		<div class="g-cellgrid__empty">
			<slot name="empty" />
		</div>
	</div>

	<div v-else-if="loading" class="g-glass g-cellgrid g-cellgrid--balance">
		<div v-for="n in cells" :key="n" class="g-cell" aria-hidden="true">
			<GSkeleton width="52%" height="27px" />
			<GSkeleton height="3px" />
			<GSkeleton width="74%" height="9px" />
		</div>
	</div>

	<div v-else class="g-glass g-cellgrid g-cellgrid--balance">
		<slot />
	</div>
</template>

<script setup>
import GSkeleton from "./GSkeleton.vue"

defineProps({
	loading: { type: Boolean, default: false },
	cells: { type: Number, default: 4 },
	empty: { type: Boolean, default: false },
})
</script>

<style scoped>
.g-cell > :deep(.g-skeleton) + :deep(.g-skeleton) {
	margin-top: 8px;
}
.g-cellgrid__empty {
	padding: var(--g-pad-panel);
}
</style>
