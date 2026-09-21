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
						<span class="whitespace-nowrap">{{
							__("−{0}h", [formatHours(props.doc.hours_cost)])
						}}</span>
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
import { computed, inject } from "vue"

import ListItem from "@/components/ListItem.vue"
import { formatHours } from "@/utils/formatters"
import { requestStatus } from "@/utils/requestStatus"

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

// English word here (the chip picks its variant from it); translated in the template.
const status = computed(() => {
	if (props.workflowStateField) return props.doc[props.workflowStateField]
	return requestStatus("Replacement Leave Claim", props.doc).label
})
</script>
