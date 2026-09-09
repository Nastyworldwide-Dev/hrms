<template>
	<ListItem
		:isTeamRequest="props.isTeamRequest"
		:employee="props.doc.employee"
		:employeeName="props.doc.employee_name"
	>
		<template #left>
			<div class="flex flex-col items-start gap-1">
				<div class="text-button-label font-semibold text-inkbase">
					{{ __("{0}h overtime", [props.doc.claimed_hours ?? 0]) }}
				</div>
				<div class="text-xs text-ink-600">
					<span>{{ props.doc.ot_date_label || props.doc.ot_date }}</span>
					<span v-if="props.doc.compensation">
						<span class="whitespace-pre"> &middot; </span>
						<span class="whitespace-nowrap">{{ __(props.doc.compensation) }}</span>
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
import { computed, inject } from "vue"

import ListItem from "@/components/ListItem.vue"
import { requestStatusChip } from "@/utils/requestStatus"

const __ = inject("$translate")

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

// The decision is in `status`; docstatus alone cannot tell Rejected from Approved.
const status = computed(() => {
	if (props.workflowStateField) return props.doc[props.workflowStateField]
	return __(requestStatusChip(props.doc))
})
</script>
