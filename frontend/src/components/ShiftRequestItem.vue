<template>
	<ListItem
		:isTeamRequest="props.isTeamRequest"
		:employee="props.doc.employee"
		:employeeName="props.doc.employee_name"
	>
		<template #left>
			<div class="flex flex-col items-start gap-1">
				<div class="text-button-label font-semibold text-inkbase">
					{{ props.doc.shift_type }}
				</div>
				<div class="text-xs text-ink-600">
					<span>{{ props.doc.shift_dates || getDates(props.doc) }}</span>
					<span v-if="props.doc.to_date">
						<span class="whitespace-pre"> &middot; </span>
						<span class="whitespace-nowrap">{{ __("{0}d", [props.doc.total_shift_days || getTotalDays(props.doc)]) }}</span>
					</span>
				</div>
			</div>
		</template>
		<template #right>
			<GStatusChip :status="status" :label="status" />
		</template>
	</ListItem>
</template>

<script setup>
import GStatusChip from "@/components/glass/GStatusChip.vue"
import { computed } from "vue"

import ListItem from "@/components/ListItem.vue"
import { getDates, getTotalDays } from "@/data/attendance"

const props = defineProps({
	doc: {
		type: Object,
	},
	isTeamRequest: {
		type: Boolean,
		default: false,
	},
	workflowStateField: {
		type: String,
		required: false,
	},
})

const status = computed(() => {
	if (props.workflowStateField) return props.doc[props.workflowStateField]
	return props.doc.docstatus ? props.doc.status : "Open"
})

</script>
