<template>
	<ListItem
		:isTeamRequest="props.isTeamRequest"
		:employee="props.doc.employee"
		:employeeName="props.doc.employee_name"
	>
		<template #left>
			<div class="flex flex-col items-start gap-1">
				<div class="text-[15px] font-semibold text-inkbase">
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
			<span class="m-chip" :class="chipMap[status] || 'm-chip-muted'">{{ status }}</span>
		</template>
	</ListItem>
</template>

<script setup>
import { computed, inject } from "vue"

import ListItem from "@/components/ListItem.vue"

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

// Same docstatus-driven model as OT Request — approval is the submit.
const status = computed(() => {
	if (props.workflowStateField) return props.doc[props.workflowStateField]
	if (props.doc.docstatus === 1) return __("Approved")
	if (props.doc.docstatus === 2) return __("Cancelled")
	return __("Pending")
})

const chipMap = computed(() => ({
	[__("Approved")]: "m-chip-outline",
	[__("Cancelled")]: "m-chip-solid",
	[__("Pending")]: "m-chip-muted",
}))
</script>
