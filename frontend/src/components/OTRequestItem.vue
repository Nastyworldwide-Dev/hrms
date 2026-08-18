<template>
	<ListItem
		:isTeamRequest="props.isTeamRequest"
		:employee="props.doc.employee"
		:employeeName="props.doc.employee_name"
	>
		<template #left>
			<div class="flex flex-col items-start gap-1">
				<div class="text-[15px] font-semibold text-inkbase">
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

// OT Request carries no status/approver field — approval IS the submit, the
// same model hrms.overrides.ot_row_scope documents. Chip reads the docstatus.
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
