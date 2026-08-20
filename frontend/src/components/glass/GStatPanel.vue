<!--
  GStatPanel — the flattened stat row (spec §15.2).

  ONE glass surface with internal --hair dividers, NOT 3 glass tiles. 3-up at
  both breakpoints (§20.5 — the stat row does not reflow at lg:).
  Child GStatTiles are cells and carry no glass.

  Props:
    loading  boolean — §11.2 skeleton cells, no spinner
    cells    number, default 3 — skeleton cell count while loading
    columns  3 (default) or 4 — §12 specifies 3-up; attendance needs 4
  Slots:
    default  — GStatTile children
-->
<template>
	<div class="g-glass g-cellgrid" :class="`g-cellgrid--stat-${columns}`">
		<template v-if="loading">
			<div v-for="n in cells" :key="n" class="g-cell g-cell--tile" aria-hidden="true">
				<GSkeleton width="46%" height="20px" />
				<GSkeleton width="78%" height="9px" />
			</div>
		</template>
		<slot v-else />
	</div>
</template>

<script setup>
import GSkeleton from "./GSkeleton.vue"

defineProps({
	loading: { type: Boolean, default: false },
	cells: { type: Number, default: 3 },
	// §12 says 3-up; the attendance calendar summarises FOUR statuses, so the
	// count is a prop rather than a hardcoded grid (v1.5: the app governs scope)
	columns: { type: Number, default: 3, validator: (n) => n === 3 || n === 4 },
})
</script>

<style scoped>
/* skeleton blocks are centred like the tile content they stand in for */
.g-cell--tile :deep(.g-skeleton) {
	margin-inline: auto;
}
.g-cell--tile :deep(.g-skeleton) + :deep(.g-skeleton) {
	margin-top: 6px;
}
</style>
