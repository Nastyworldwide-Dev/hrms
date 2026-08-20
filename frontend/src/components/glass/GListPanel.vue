<!--
  GListPanel — the glass container GListRow sits in (spec §10.1 #3, §15.1).

  THE SURFACE BOUNDARY: this component carries .g-glass; its rows do not.
  Container + child rows = ONE surface against the §15 budget of 6. Never put
  a glass component (GIssueCard, GNotePanel, GGhostButton) inside it — that
  nests glass, which §15 forbids.
  Identical at both breakpoints (§20.7).

  Props:
    loading   boolean — §11.2 skeleton rows instead of content, no spinner
    rows      number, default 3 — how many skeleton rows while loading
    empty     boolean — render the empty slot instead of content (§11.1)
  Slots:
    default   — GListRow children
    empty     — shown when `empty`; use GEmptyState with §11.1 copy
-->
<template>
	<div class="g-glass g-list">
		<template v-if="loading">
			<div v-for="n in rows" :key="n" class="g-row" aria-hidden="true">
				<GSkeleton width="27px" height="27px" radius="var(--g-radius-well)" />
				<span class="g-row__body">
					<GSkeleton width="58%" height="11px" />
				</span>
			</div>
			<span class="g-list__sr">{{ __("Loading") }}</span>
		</template>

		<div v-else-if="empty" class="g-list__empty">
			<slot name="empty" />
		</div>

		<slot v-else />
	</div>
</template>

<script setup>
import GSkeleton from "./GSkeleton.vue"

defineProps({
	loading: { type: Boolean, default: false },
	rows: { type: Number, default: 3 },
	empty: { type: Boolean, default: false },
})
</script>

<style scoped>
/* skeleton rows reuse .g-row spacing; only the announcement is local */
.g-list__sr {
	position: absolute;
	width: 1px;
	height: 1px;
	overflow: hidden;
	clip-path: inset(50%);
}
.g-list__empty {
	padding: var(--g-pad-panel);
}
</style>
