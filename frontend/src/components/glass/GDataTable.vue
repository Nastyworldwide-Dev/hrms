<!--
  GDataTable — payslip and expense line items (spec §10.3 treatment list).

  §6.3, AND THIS IS ITS CLEAREST CASE: "a number a person may dispute with
  their manager must not be read through a moving tint". Payslip figures are
  exactly that. The surface is SOLID (--glass-fill-fallback), there is no
  backdrop-filter, and no track or divider is translucent beyond --hair.
  Do not apply glass to this for visual consistency — §6.3 forbids it by name.

  Every figure is tabular (§4.3) and right-aligned; label columns stay left.
  Identical at both breakpoints (§20.7). Wide tables scroll inside their own
  container rather than pushing the page sideways.

  Props:
    columns  array, required — [{ key, label, numeric }]
    rows     array, required — [{ [key]: value }]; a row with `total: true`
             gets the total rule and weight
    caption  string — accessible table caption, e.g. "August 2026 payslip"
    loading  boolean — §11.2 skeleton rows, no spinner
    skeletonRows number, default 4
  Slot: empty — §11.1 empty state, shown when rows is empty and not loading
-->
<template>
	<!-- The scroll container is focusable and named: with two wide text columns
	     (Team KPI's employee + department) the table overflows a 375px viewport,
	     and an unfocusable overflow region leaves the right-hand columns
	     unreachable by keyboard (WCAG 2.1.1).
	     Only the ROLE is gated on `caption`: Vue renders :aria-label="''" as an
	     EMPTY attribute rather than dropping it (only `null` removes it), so a
	     caption-less caller would ship a nameless role="region", which ARIA does
	     not expose as a landmark at all. The tab stop stays unconditional — an
	     unnamed focusable scroller is fine, and gating it would hand the 2.1.1
	     defect straight back to the first caption-less caller with wide columns.
	     `g-focusable` keeps the §14.3 ring, so the one focusable surface this
	     component owns does not look like a different application. -->
	<div
		class="g-table__scroll g-focusable"
		tabindex="0"
		:role="caption ? 'region' : null"
		:aria-label="caption || null"
	>
		<table class="g-table">
			<caption v-if="caption" class="g-sr">
				{{
					caption
				}}
			</caption>
			<thead>
				<tr>
					<th
						v-for="col in columns"
						:key="col.key"
						:class="{ 'g-table__num': col.numeric }"
						:scope="'col'"
					>
						{{ col.label }}
					</th>
				</tr>
			</thead>
			<tbody>
				<template v-if="loading">
					<tr v-for="n in skeletonRows" :key="n" aria-hidden="true">
						<td v-for="col in columns" :key="col.key">
							<GSkeleton height="11px" :width="col.numeric ? '52%' : '78%'" />
						</td>
					</tr>
				</template>

				<tr v-else-if="!rows.length">
					<td :colspan="columns.length">
						<slot name="empty" />
					</td>
				</tr>

				<template v-else>
					<tr v-for="(row, i) in rows" :key="i" :class="{ 'g-table__total': row.total }">
						<td v-for="col in columns" :key="col.key" :class="{ 'g-table__num': col.numeric }">
							<!-- A REAL BUTTON, never a click handler on the <tr>. A row
							     with an onclick is not keyboard-reachable and is
							     announced as plain text, so the only way into a detail
							     view would be a mouse. The cell that names the thing is
							     the one that opens it. -->
							<button
								v-if="col.action"
								type="button"
								class="g-table__action g-focusable"
								@click="$emit('row-action', row)"
							>
								{{ row[col.key] }}
							</button>
							<template v-else>{{ row[col.key] }}</template>
						</td>
					</tr>
				</template>
			</tbody>
		</table>
	</div>
</template>

<script setup>
import GSkeleton from "./GSkeleton.vue"

defineEmits(["row-action"])

defineProps({
	// columns: [{ key, label, numeric, action }] — `action` renders the cell as
	// a button that emits row-action with the whole row.
	columns: { type: Array, required: true },
	rows: { type: Array, default: () => [] },
	caption: { type: String, default: "" },
	loading: { type: Boolean, default: false },
	skeletonRows: { type: Number, default: 4 },
})
</script>

<style scoped>
/* An action cell must not look like a link dropped into a data table: it keeps
   the row's own type and colour and earns its affordance from the underline
   and the focus ring, the same way .g-seclink does elsewhere. */
.g-table__action {
	background: none;
	border: 0;
	padding: 0;
	font: inherit;
	color: inherit;
	text-align: inherit;
	text-decoration: underline;
	text-underline-offset: 3px;
	cursor: pointer;
}

/* numeric cells right-align inside the shared .g-table padding */
.g-table__num :deep(.g-skeleton) {
	margin-left: auto;
}
</style>
