<template>
	<ListItem
		:isTeamRequest="props.isTeamRequest"
		:employee="props.doc.employee"
		:employeeName="props.doc.employee_name"
	>
		<template #left>
			<div class="flex flex-col items-start gap-1 min-w-0 max-w-full">
				<div
					class="text-button-label font-semibold text-inkbase truncate max-w-full"
					:title="title"
				>
					{{ title }}
				</div>
				<div class="text-xs text-ink-600">{{ subline }}</div>
				<!-- How long it has been waiting, while it waits. A manpower request names no
				     approver on the row, so this reads "waiting 2 days ago" (utils/requestWaiting.js). -->
				<div v-if="waiting" class="text-xs text-ink-500">{{ waiting }}</div>
			</div>
		</template>
		<template #right>
			<GStatusChip :status="where.status" :label="__(where.label)" />
		</template>
	</ListItem>
</template>

<script setup>
import { computed, inject } from "vue"

import ListItem from "@/components/ListItem.vue"
import GStatusChip from "@/components/glass/GStatusChip.vue"
import { departmentLabel } from "@/utils/departmentLabel"
import { stage } from "@/utils/manpowerRequest"
import { requestStatus } from "@/utils/requestStatus"
import { waitingWith } from "@/utils/requestWaiting"
import { siteTime } from "@/utils/siteTime"

const __ = inject("$translate")

const props = defineProps({
	doc: { type: Object },
	isTeamRequest: { type: Boolean, default: false },
	workflowStateField: { type: String, required: false },
})

//: "Driver ×3": the title, the count after it when there is more than one.
const title = computed(() => {
	const count = Number(props.doc.headcount) > 1 ? ` ×${props.doc.headcount}` : ""
	return `${props.doc.position_title || __("Manpower request")}${count}`
})
const where = computed(() => stage(props.doc))
//: Never on a TEAM row: an approver reading their own queue knows who it is with.
const waiting = computed(() =>
	props.isTeamRequest
		? ""
		: waitingWith(props.doc, {
				pending: requestStatus("Manpower Request", props.doc).pending,
				since: (date) => siteTime(date).fromNow(),
				t: __,
		  })
)
//: "Ops · High urgency · Sent 20 Oct" — what it is, how pressing, when it went.
const subline = computed(() =>
	[
		departmentLabel(props.doc.department),
		props.doc.urgency ? __("{0} urgency", [__(props.doc.urgency)]) : "",
		props.doc.creation ? __("Sent {0}", [siteTime(props.doc.creation).format("D MMM")]) : "",
	]
		.filter(Boolean)
		.join(" · ")
)
</script>
