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
						<span class="whitespace-nowrap">{{ daysWords(getTotalDays(props.doc)) }}</span>
					</span>
				</div>
				<!-- WHO it is with, and since when. A chip reading "Waiting"
				     does not say on whom (mockup 4 gap #1). Renders nothing when
				     there is nothing true to say. -->
				<div v-if="waiting" class="text-xs text-ink-500">{{ waiting }}</div>
			</div>
		</template>
		<template #right>
			<GStatusChip :status="status" :label="__(status)" />
		</template>
	</ListItem>
</template>

<script setup>
import { daysWords } from "@/utils/countWords"
import { siteTime } from "@/utils/siteTime"
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
	workflowStateField: {
		type: String,
		required: false,
	},
})

const status = computed(() => {
	if (props.workflowStateField) return props.doc[props.workflowStateField]
	return requestStatus("Attendance Request", props.doc).label
})

//: WHO it is with, and since when (mockup 4 gap #1). Never on a TEAM row:
//: an approver reading their own queue knows who it is with.
const waiting = computed(() =>
	props.isTeamRequest
		? ""
		: waitingWith(props.doc, {
				pending: requestStatus("Attendance Request", props.doc).pending,
				since: (date) => siteTime(date).fromNow(),
				t: __,
		  })
)
</script>
