<template>
	<ListItem
		:isTeamRequest="props.isTeamRequest"
		:employee="props.doc.employee"
		:employeeName="props.doc.employee_name"
	>
		<template #left>
			<div class="flex flex-col items-start gap-1">
				<div class="text-button-label font-semibold text-inkbase">
					{{ claimTitle }}
				</div>
				<div class="text-xs text-ink-600">
					<span>{{ claimDates }}</span>
					<span class="whitespace-pre"> &middot; </span>
					<span class="whitespace-nowrap">
						{{ formatCurrency(props.doc.total_claimed_amount, props.doc.currency) }}
					</span>
				</div>
			</div>
		</template>
		<template #right>
			<GStatusChip :status="status" :label="__(status, null, 'Expense Claim')" />
		</template>
	</ListItem>
</template>

<script setup>
import GStatusChip from "@/components/glass/GStatusChip.vue"
import { computed, inject } from "vue"

import ListItem from "@/components/ListItem.vue"

import { formatCurrency } from "@/utils/formatters"

const dayjs = inject("$dayjs")
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

const status = computed(() => {
	if (props.workflowStateField) {
		return props.doc[props.workflowStateField]
	} else if (
		props.doc.approval_status === "Approved" &&
		["Draft", "Unpaid", "Submitted"].includes(props.doc.status)
	) {
		return `${props.doc.approval_status} & ${props.doc.status}`
	} else if (props.doc.approval_status === "Rejected") {
		return "Rejected"
	}
	return props.doc.status
})

const claimTitle = computed(() => {
	let title = __(props.doc.expense_type)
	if (props.doc.total_expenses > 1) {
		title = __("{0} & {1} more", [title, props.doc.total_expenses - 1])
	}
	return title
})

const claimDates = computed(() => {
	if (!props.doc.from_date && !props.doc.to_date)
		return dayjs(props.doc.posting_date).format("D MMM")

	if (props.doc.from_date === props.doc.to_date) {
		return dayjs(props.doc.from_date).format("D MMM")
	} else {
		return `${dayjs(props.doc.from_date).format("D MMM")} - ${dayjs(props.doc.to_date).format(
			"D MMM"
		)}`
	}
})
</script>
