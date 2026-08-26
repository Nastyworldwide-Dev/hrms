<template>
	<ListItem
		:isTeamRequest="props.isTeamRequest"
		:employee="props.doc.employee"
		:employeeName="props.doc.employee_name"
	>
		<template #left>
			<div class="flex flex-col items-start gap-1">
				<div class="text-button-label font-semibold text-inkbase">
					{{ props.doc.reason }}
				</div>
				<div class="text-xs text-ink-600">
					<span>{{ props.doc.attendance_dates || getDates(props.doc) }}</span>
					<span v-if="getTotalDays(props.doc) > 0">
						<span class="whitespace-pre"> &middot; </span>
						<span class="whitespace-nowrap">{{ __("{0}d", [getTotalDays(props.doc)]) }}</span>
					</span>
				</div>
			</div>
		</template>
		<template #right>
			<GStatusChip :status="status" :label="__(status)" />
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
	workflowStateField: {
		type: String,
		required: false,
	},
})

const status = computed(() => {
	if (props.workflowStateField) return props.doc[props.workflowStateField]
	return props.doc.docstatus ? "Submitted" : "Draft"
})
</script>
