<template>
	<ListItem
		:isTeamRequest="props.isTeamRequest"
		:employee="props.doc.employee"
		:employeeName="props.doc.employee_name"
	>
		<template #left>
			<div class="flex flex-col items-start gap-1">
				<!-- The OUTCOME first, the input second (2.0 slice 2.2). An
				     employee knows how long they stayed; what they opened this
				     to find out is whether it became pay or a day off. So the
				     row leads with that and carries the hours as the detail
				     they belong to. -->
				<div class="text-button-label font-semibold text-inkbase">
					{{ outcome }}
				</div>
				<div class="text-xs text-ink-600">
					<span>{{ props.doc.ot_date_label || props.doc.ot_date }}</span>
					<template v-if="hoursAsTime(props.doc.claimed_hours)">
						<span class="whitespace-pre"> &middot; </span>
						<span class="whitespace-nowrap">
							{{ hoursAsTime(props.doc.claimed_hours) }}
						</span>
					</template>
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
//: The wire values of `compensation`, which are the doctype's Select options
//: and cannot change without a migration. Mapping them EXPLICITLY, rather than
//: passing the raw value through `__()`, is what keeps the server's vocabulary
//: off the screen — and makes it visible here which two words exist.
const OUTCOME = {
	"Overtime Pay": () => __("Overtime pay"),
	"Replacement Leave": () => __("A day off in return"),
}

//: What the claim turned into. Before a decision there is nothing to state, so
//: it falls back to the hours — the row still has to say what it is about.
const outcome = computed(() => {
	const chosen = OUTCOME[props.doc.compensation]
	if (chosen) return chosen()
	const hours = hoursAsTime(props.doc.claimed_hours)
	return hours ? __("{0} overtime", [hours]) : __("Overtime")
})

const status = computed(() => {
	if (props.workflowStateField) return props.doc[props.workflowStateField]
	return requestStatus("OT Request", props.doc).label
})

//: WHO it is with, and since when (mockup 4 gap #1). Never on a TEAM row:
//: an approver reading their own queue knows who it is with.
const waiting = computed(() =>
	props.isTeamRequest
		? ""
		: waitingWith(props.doc, {
				pending: requestStatus("OT Request", props.doc).pending,
				since: (date) => siteTime(date).fromNow(),
				t: __,
		  })
)
</script>
