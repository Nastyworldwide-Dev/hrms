<!--
  GStatPanel — the flattened stat row (spec §15.2).

  ONE glass surface with internal --hair dividers, NOT 3 glass tiles. 3-up at
  both breakpoints (§20.5 — the stat row does not reflow at lg:).
  Child GStatTiles are cells and carry no glass.

  Props:
    loading  boolean — §11.2 skeleton cells, no spinner
    cells    number, default 3 — skeleton cell count while loading
  Slots:
    default  — GStatTile children
-->
<template>
	<div class="g-glass g-cellgrid g-cellgrid--stat">
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
