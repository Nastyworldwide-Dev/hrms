<template>
	<ListItem
		:isTeamRequest="props.isTeamRequest"
		:employee="props.doc.employee"
		:employeeName="props.doc.employee_name"
	>
		<template #left>
			<div class="flex flex-col items-start gap-1">
				<div class="text-button-label font-semibold text-inkbase">
					{{ __(props.doc.leave_type, null, "Leave Type") }}
				</div>
				<div class="text-xs text-ink-600">
					<span>{{ props.doc.leave_dates || getLeaveDates(props.doc) }}</span>
					<span class="whitespace-pre"> &middot; </span>
					<span class="whitespace-nowrap">{{ daysWords(props.doc.total_leave_days) }}</span>
				</div>
				<!-- WHO it is with, and since when. A chip reading "Waiting" does
				     not say on whom, and the employee looking at their own list is
				     almost always trying to work out who to chase (mockup 4 gap
				     #1). Renders nothing when there is nothing true to say. -->
				<div v-if="waiting" class="text-xs text-ink-500">{{ waiting }}</div>
			</div>
		</template>
		<template #right>
			<GStatusChip :status="status" :label="__(status, null, 'Leave Application')" />
		</template>
	</ListItem>
</template>

<script setup>
import { daysWords } from "@/utils/countWords"
import { siteTime } from "@/utils/siteTime"
import GStatusChip from "@/components/glass/GStatusChip.vue"
import { computed, inject } from "vue"

import ListItem from "@/components/ListItem.vue"
import { getLeaveDates } from "@/data/leaves"
import { requestStatus } from "@/utils/requestStatus"
import { waitingWith } from "@/utils/requestWaiting"

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

const __ = inject("$translate")
const $dayjs = inject("$dayjs")

const verdict = computed(() => requestStatus("Leave Application", props.doc))

const status = computed(() => {
	if (props.workflowStateField) return props.doc[props.workflowStateField]
	return verdict.value.label
})

//: Never on a TEAM row. An approver looking at their own queue knows who it is
//: with — themselves — and the line would be one wasted row per request.
const waiting = computed(() =>
	props.isTeamRequest
		? ""
		: waitingWith(props.doc, {
				pending: verdict.value.pending,
				since: (date) => siteTime(date).fromNow(),
				t: __,
		  })
)
</script>
