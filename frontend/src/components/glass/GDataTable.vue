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
	<div class="g-table__scroll">
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
							{{ row[col.key] }}
						</td>
					</tr>
				</template>
			</tbody>
		</table>
	</div>
</template>

<script setup>
import GSkeleton from "./GSkeleton.vue"

defineProps({
	columns: { type: Array, required: true },
	rows: { type: Array, default: () => [] },
	caption: { type: String, default: "" },
	loading: { type: Boolean, default: false },
	skeletonRows: { type: Number, default: 4 },
})
</script>

<style scoped>
/* numeric cells right-align inside the shared .g-table padding */
.g-table__num :deep(.g-skeleton) {
	margin-left: auto;
}
</style>
