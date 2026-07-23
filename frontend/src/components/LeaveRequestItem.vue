<template>
	<ListItem
		:isTeamRequest="props.isTeamRequest"
		:employee="props.doc.employee"
		:employeeName="props.doc.employee_name"
	>
		<template #left>
			<div class="flex flex-col items-start gap-1">
				<div class="text-[15px] font-semibold text-inkbase">
					{{ __(props.doc.leave_type, null, "Leave Type") }}
				</div>
				<div class="text-xs text-ink-600">
					<span>{{ props.doc.leave_dates || getLeaveDates(props.doc) }}</span>
					<span class="whitespace-pre"> &middot; </span>
					<span class="whitespace-nowrap">{{ __("{0}d", [props.doc.total_leave_days]) }}</span>
				</div>
			</div>
		</template>
		<template #right>
			<span class="m-chip" :class="chipMap[status] || 'm-chip-muted'">{{ __(status, null, 'Leave Application') }}</span>
		</template>
	</ListItem>
</template>

<script setup>
import { computed } from "vue"

import ListItem from "@/components/ListItem.vue"
import { getLeaveDates } from "@/data/leaves"

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
	return props.workflowStateField ? props.doc[props.workflowStateField] : props.doc.status
})

const chipMap = {
	Approved: "m-chip-outline",
	Rejected: "m-chip-solid",
	Open: "m-chip-muted",
}
</script>
