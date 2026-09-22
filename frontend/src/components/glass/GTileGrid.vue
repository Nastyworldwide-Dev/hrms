<!--
  GTileGrid — the flattened tile grid (spec §15.2), 4-up.

  ONE glass surface with internal --hair dividers, NOT N tiles-as-cards. Sibling
  of GStatPanel (3/4-up stats) and GBalanceGrid (2-up balances); this one carries
  a wrapping grid of small destinations, so it owns the empty state as well.

  It exists as a primitive rather than markup inside its caller because the
  surface class belongs to this directory — that is what the usage gate enforces
  and what keeps the §15 surface counter able to see one panel instead of N.

  Props:
    loading  boolean — §11.2 skeleton tiles, no spinner
    tiles    number, default 7 — skeleton tile count while loading
    empty    boolean — render the empty slot instead of content (§11.1)
  Slots:
    default  — .g-cell.g-cell--quick children (buttons or links)
    empty    — shown when `empty`; use GEmptyState with §11.1 copy
-->
<template>
	<!-- One surface for every state, as GBalanceGrid does it: empty, loading and
	     filled are mutually-exclusive content INSIDE the single panel. Three
	     sibling panels would read as three surfaces to the static counter even
	     though only one ever renders. -->
	<div class="g-glass" :class="empty ? 'g-list' : ['g-cellgrid', 'g-cellgrid--quick']">
		<div v-if="empty" class="g-tilegrid__empty">
			<slot name="empty" />
		</div>

		<template v-else-if="loading">
			<div v-for="n in tiles" :key="n" class="g-cell g-cell--quick" aria-hidden="true">
				<GSkeleton width="20px" height="20px" radius="var(--g-radius-well)" />
				<GSkeleton width="80%" height="9px" />
			</div>
		</template>

		<slot v-else />
	</div>
</template>

<script setup>
import GSkeleton from "./GSkeleton.vue"

defineProps({
	loading: { type: Boolean, default: false },
	// Seven is the count the grid settles at on Home (six base quick links plus
	// the HR row). Matching it matters only for the ROW count: seven and eight
	// both fill two rows of four, but a four-tile default would make the panel
	// jump a row when the real tiles land.
	tiles: { type: Number, default: 7 },
	empty: { type: Boolean, default: false },
})
</script>

<style scoped>
/* The grid zeroes its padding so the cells can draw the dividers; the empty
   state is the one child that needs the panel's padding back. */
.g-tilegrid__empty {
	padding: var(--g-pad-panel);
}
</style>
