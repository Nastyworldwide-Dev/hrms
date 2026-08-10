<template>
	<ListItem
		:isTeamRequest="props.isTeamRequest"
		:employee="props.doc.employee"
		:employeeName="props.doc.employee_name"
	>
		<template #left>
			<div class="flex flex-col items-start gap-1">
				<div class="text-[15px] font-semibold text-inkbase">
					{{ __(props.doc.purpose) }}
				</div>
				<div class="text-xs text-ink-600">
					{{ __("Paid {0}", [formatCurrency(props.doc.paid_amount, props.doc.currency)]) }}
				</div>
			</div>
		</template>
		<template #right>
			<span class="text-[15px] font-bold tabular-nums text-inkbase">
				{{ formatCurrency(props.doc.balance_amount || props.doc.advance_amount, props.doc.currency) }}
			</span>
		</template>
	</ListItem>
</template>

<script setup>
import ListItem from "@/components/ListItem.vue"
import { formatCurrency } from "@/utils/formatters"

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
</script>
