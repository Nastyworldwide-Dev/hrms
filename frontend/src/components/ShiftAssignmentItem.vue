<template>
	<ListItem>
		<template #left>
			<div class="flex flex-col items-start gap-1">
				<div class="text-button-label font-semibold text-inkbase">
					{{ props.doc.shift_type }}
				</div>
				<div class="text-xs text-ink-600">
					<span>{{ props.doc.shift_dates || getShiftDates(props.doc) }}</span>
					<span v-if="props.doc.end_date" class="whitespace-pre"> &middot; </span>
					<span v-if="props.doc.end_date" class="whitespace-nowrap">{{
						__("{0}d", [props.doc.total_shift_days || getTotalShiftDays(props.doc)])
					}}</span>
				</div>
				<div
					v-if="props.doc.shift_location"
					class="text-xs text-ink-600 whitespace-nowrap"
				>
					&#128205; {{ props.doc.shift_location }}
				</div>
			</div>
		</template>
		<template #right>
			<span v-if="props.doc.shift_timing" class="text-xs font-bold tabular-nums text-inkbase">
				{{ props.doc.shift_timing }}
			</span>
			<GStatusChip v-else :status="status" :label="status" />
		</template>
	</ListItem>
</template>

<script setup>
import GStatusChip from "@/components/glass/GStatusChip.vue"
import { computed } from "vue"

import ListItem from "@/components/ListItem.vue"
import { getShiftDates, getTotalShiftDays } from "@/data/attendance"

const props = defineProps({
	doc: {
		type: Object,
	},
})

const status = computed(() => {
	if (props.workflowStateField) return props.doc[props.workflowStateField]
	return props.doc.docstatus ? "Submitted" : "Draft"
})
</script>
