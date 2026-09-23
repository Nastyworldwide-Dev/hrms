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
						<span class="whitespace-nowrap">{{
							__("{0}d", [props.doc.total_shift_days || getTotalDays(props.doc)])
						}}</span>
					</span>
				</div>
				<!-- WHO it is with, and since when. A chip reading "Waiting"
				     does not say on whom (mockup 4 gap #1). Renders nothing when
				     there is nothing true to say. -->
				<div v-if="waiting" class="text-xs text-ink-500">{{ waiting }}</div>
			</div>
		</template>
		<template #right>
			<GStatusChip :status="status" :label="__(status, null, 'Shift Request')" />
		</template>
	</ListItem>
</template>

<script setup>
import GStatusChip from "@/components/glass/GStatusChip.vue"
import { computed, inject } from "vue"

import ListItem from "@/components/ListItem.vue"
import { getDates, getTotalDays } from "@/data/attendance"
import { requestStatus } from "@/utils/requestStatus"
import { waitingWith } from "@/utils/requestWaiting"

// Needed in the SCRIPT now, not just the template: the "with whom"
// line is built in a computed, and Vue only resolves __ for templates.
const __ = inject("$translate")
const dayjs = inject("$dayjs")

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
	return requestStatus("Shift Request", props.doc).label
})

//: WHO it is with, and since when (mockup 4 gap #1). Never on a TEAM row:
//: an approver reading their own queue knows who it is with.
const waiting = computed(() =>
	props.isTeamRequest
		? ""
		: waitingWith(props.doc, {
				pending: requestStatus("Shift Request", props.doc).pending,
				since: (date) => dayjs(date).fromNow(),
				t: __,
		  })
)
</script>
