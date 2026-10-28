<template>
	<ListItem
		:isTeamRequest="props.isTeamRequest"
		:employee="props.doc.employee"
		:employeeName="props.doc.employee_name"
	>
		<template #left>
			<span
				class="g-row__well g-row__well--tile"
				:style="{ background: TILE.sop }"
				aria-hidden="true"
			>
				<Users class="g-row-icon" />
			</span>
			<div class="flex flex-col items-start gap-1 min-w-0 max-w-full">
				<div
					class="text-button-label font-semibold text-inkbase truncate max-w-full"
					:title="title"
				>
					{{ title }}
				</div>
				<!-- "Sent 22 Oct · 5 days waiting"; once Closed the last word is the reason (Withdrawn, Rejected, Not proceeding). -->
				<div class="text-xs text-ink-600">{{ subline }}</div>
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
import { Users } from "lucide-vue-next"

import ListItem from "@/components/ListItem.vue"
import GStatusChip from "@/components/glass/GStatusChip.vue"
import { listSubline } from "@/utils/manpowerBoard"
import { requestStatus } from "@/utils/requestStatus"
import { waitingWith } from "@/utils/requestWaiting"
import { stage } from "@/utils/manpowerRequest"
import { siteTime } from "@/utils/siteTime"
import { TILE } from "@/utils/iconTile"

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
const waiting = computed(() =>
	props.isTeamRequest
		? ""
		: waitingWith(props.doc, {
				pending: requestStatus("Manpower Request", props.doc).pending,
				since: (date) => siteTime(date).fromNow(),
				t: __,
		  })
)
const subline = computed(() => listSubline(props.doc, { t: __, ownWaitingLine: true }))
</script>
