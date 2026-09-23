<template>
	<ListItem
		:isTeamRequest="props.isTeamRequest"
		:employee="props.doc.employee"
		:employeeName="props.doc.employee_name"
	>
		<template #left>
			<div class="flex flex-col items-start gap-1">
				<div class="text-button-label font-semibold text-inkbase">
					{{ countOf(props.doc.claimed_days ?? 0, __("replacement day")) }}
				</div>
				<div class="text-xs text-ink-600">
					<span>{{ props.doc.bank_month_label || props.doc.bank_month }}</span>
					<span v-if="props.doc.hours_cost">
						<span class="whitespace-pre"> &middot; </span>
						<span class="whitespace-nowrap">{{
							__("−{0}", [hoursAsTime(props.doc.hours_cost)])
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
			<GStatusChip :status="status" :label="__(status)" />
		</template>
	</ListItem>
</template>

<script setup>
import { siteTime } from "@/utils/siteTime"
import GStatusChip from "@/components/glass/GStatusChip.vue"
import { computed, inject } from "vue"

import ListItem from "@/components/ListItem.vue"
import { hoursAsTime } from "@/utils/daySheet"
import { requestStatus } from "@/utils/requestStatus"
import { waitingWith } from "@/utils/requestWaiting"
import { countOf } from "@/utils/countWords"

const __ = inject("$translate")
const $dayjs = inject("$dayjs")

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

//: WHO it is with, and since when (mockup 4 gap #1). Never on a TEAM row:
//: an approver reading their own queue knows who it is with.
const waiting = computed(() =>
	props.isTeamRequest
		? ""
		: waitingWith(props.doc, {
				pending: requestStatus("Replacement Leave Claim", props.doc).pending,
				since: (date) => siteTime(date).fromNow(),
				t: __,
		  })
)
</script>
