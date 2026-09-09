<template>
	<ListItem
		:isTeamRequest="props.isTeamRequest"
		:employee="props.doc.employee"
		:employeeName="props.doc.employee_name"
	>
		<template #left>
			<div class="flex flex-col items-start gap-1">
				<div class="text-button-label font-semibold text-inkbase">
					{{ __("{0} replacement day(s)", [props.doc.claimed_days ?? 0]) }}
				</div>
				<div class="text-xs text-ink-600">
					<span>{{ props.doc.bank_month_label || props.doc.bank_month }}</span>
					<span v-if="props.doc.hours_cost">
						<span class="whitespace-pre"> &middot; </span>
						<span class="whitespace-nowrap">{{ __("−{0}h", [props.doc.hours_cost]) }}</span>
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
