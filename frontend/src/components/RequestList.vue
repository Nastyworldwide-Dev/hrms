<template>
	<ResourceError v-if="props.resource?.error" :resource="props.resource" :what="props.what" />
	<div class="flex flex-col overflow-auto" v-else-if="props.items?.length">
		<div
			class="flex flex-row py-3 items-center justify-between border-b border-divider cursor-pointer"
			v-for="link in props.items"
			:key="link.name"
			role="button"
			tabindex="0"
			@click="openRequestModal(link)"
			@keydown.enter.prevent="openRequestModal(link)"
			@keydown.space.prevent="openRequestModal(link)"
		>
			<!-- One line per request (one-screen Requests, 23 Sep): what it is,
			     when it was filed, and its status. The full row is in See all. -->
			<template v-if="props.compact">
				<span class="text-sm text-ink truncate">
					{{ __(REQUEST_KIND[link.doctype] || link.doctype) }}
					<span class="text-ink-600"> · {{ filedOn(link) }}</span>
				</span>
				<GStatusChip
					:status="requestStatus(link.doctype, link).label"
					:label="__(requestStatus(link.doctype, link).label)"
				/>
			</template>
			<component
				v-else
				:is="props.component || link.component"
				:doc="link"
				:workflowStateField="link.workflow_state_field"
				:isTeamRequest="props.teamRequests"
			/>
		</div>

		<router-link
			v-if="props.addListButton"
			:to="{ name: props.listButtonRoute }"
			v-slot="{ navigate }"
		>
			<!-- A text control under a list, the same one "See all" uses — not a
			     frappe-ui Button (no frappe-ui controls in the app). -->
			<button
				type="button"
				class="g-focusable g-list-more w-full py-3 text-sm text-ink-600 bg-transparent border-none"
				@click="navigate"
			>
				{{ __("See all") }}
			</button>
		</router-link>
	</div>
	<!-- Four states (D6): while the owning resource's first read is in
	     flight, skeleton rows — not "Nothing here yet", which is a claim. -->
	<div
		v-else-if="props.resource?.loading"
		class="flex flex-col gap-3 py-3"
		role="status"
		:aria-label="__('Loading')"
	>
		<GSkeleton v-for="n in 3" :key="n" height="20px" />
	</div>
	<!-- §11.1: callers pass the copy for their list; this is the fallback for
	     any that has not yet been given one -->
	<GEmptyState
		v-else
		:title="emptyStateTitle || __('Nothing here yet')"
		:body="emptyStateMessage || __('Requests you send show up here.')"
	/>

	<GModal :is-open="isRequestModalOpen" @did-dismiss="closeRequestModal">
		<RequestActionSheet :fields="fieldsMap[selectedRequest?.doctype]" v-model="selectedRequest" />
	</GModal>
</template>

<script setup>
import GEmptyState from "@/components/glass/GEmptyState.vue"
import GSkeleton from "@/components/glass/GSkeleton.vue"
import GStatusChip from "@/components/glass/GStatusChip.vue"
import { REQUEST_KIND } from "@/utils/requestKind"
import { requestStatus } from "@/utils/requestStatus"
import { siteTime } from "@/utils/siteTime"
import { ref, inject } from "vue"
import GModal from "@/components/glass/GModal.vue"
import RequestActionSheet from "@/components/RequestActionSheet.vue"

import {
	LEAVE_FIELDS,
	EXPENSE_CLAIM_FIELDS,
	ATTENDANCE_REQUEST_FIELDS,
	SHIFT_REQUEST_FIELDS,
	SHIFT_FIELDS,
	OT_REQUEST_FIELDS,
	REPLACEMENT_LEAVE_CLAIM_FIELDS,
} from "@/data/config/requestSummaryFields"

const __ = inject("$translate")
const props = defineProps({
	component: {
		type: Object,
	},
	items: {
		type: Array,
	},
	teamRequests: {
		type: Boolean,
		default: false,
	},
	// One line per row: kind, date filed, status (the Requests page's last 5).
	compact: {
		type: Boolean,
		default: false,
	},
	addListButton: {
		type: Boolean,
		default: false,
	},
	listButtonRoute: {
		type: String,
		default: "",
	},
	emptyStateTitle: {
		type: String,
		default: "",
	},
	emptyStateMessage: {
		type: String,
		default: "",
	},
	// Optional owning resource. When passed and it errored, the list shows the
	// "could not load" state instead of the empty state — so a failed fetch is
	// never mistaken for "nothing here". Callers that don't pass it are
	// unchanged.
	resource: {
		type: Object,
		default: null,
	},
	what: {
		type: String,
		default: "",
	},
})

const fieldsMap = {
	"Leave Application": LEAVE_FIELDS,
	"Expense Claim": EXPENSE_CLAIM_FIELDS,
	"Attendance Request": ATTENDANCE_REQUEST_FIELDS,
	"Shift Request": SHIFT_REQUEST_FIELDS,
	"Shift Assignment": SHIFT_FIELDS,
	"OT Request": OT_REQUEST_FIELDS,
	"Replacement Leave Claim": REPLACEMENT_LEAVE_CLAIM_FIELDS,
}

//: "21 Sep" on the site clock (the Date constructor rejects these strings on
//: Safari, I-F3).
function filedOn(request) {
	return request.creation ? siteTime(request.creation).format("D MMM") : ""
}

const isRequestModalOpen = ref(false)
const selectedRequest = ref(null)

const openRequestModal = async (request) => {
	selectedRequest.value = request
	isRequestModalOpen.value = true
}

const closeRequestModal = async () => {
	isRequestModalOpen.value = false
	selectedRequest.value = null
}
</script>
