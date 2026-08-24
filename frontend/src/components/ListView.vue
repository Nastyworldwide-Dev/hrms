<template>
	<ion-header class="ion-no-border">
		<div class="w-full sm:max-w-2xl sm:mx-auto lg:max-w-none lg:mx-0">
			<div
				class="flex flex-row bg-ground py-4 px-3 items-center justify-between border-b border-divider lg:h-16 lg:px-7 lg:py-0 lg:border-b-2"
			>
				<div class="flex flex-row items-center">
					<GIconButton :label="__('Back')" flush class="mr-1" @click="router.back()">
						<FeatherIcon name="chevron-left" class="h-5 w-5 text-inkbase" />
					</GIconButton>
					<h2 class="text-xl font-extrabold text-inkbase tracking-tight">{{ pageTitle }}</h2>
				</div>

				<div class="flex flex-row gap-2">
					<!-- GIconButton, not frappe-ui Button: an aria-label bound onto the
					     latter rendered as aria-label="" — it does not forward the attr —
					     so this stayed the last button-name violation in the app after
					     every other icon-only control was fixed. -->
					<GIconButton
						id="show-filter-modal"
						:label="__('Filter list')"
						class="g-iconbtn--boxed"
						:class="areFiltersApplied ? 'g-iconbtn--on' : ''"
					>
						<FeatherIcon name="filter" class="h-4 w-4" />
					</GIconButton>
					<!-- A create action is a GButton wherever it appears (§18, v1.11).
					     This was a white frappe-ui pill in the header while the same
					     "create a new X" role rendered as a chartreuse GButton on the
					     dashboards — one role, two components, two colours. -->
					<router-link
						v-if="createPermission?.data?.has_permission && props.doctype != 'Employee Checkin'"
						:to="{ name: formViewRoute }"
						v-slot="{ navigate }"
						class="mr-2 shrink-0"
					>
						<GButton :label="__('New', null, props.doctype)" class="g-btn--compact" @click="navigate" />
					</router-link>
				</div>
			</div>
		</div>
	</ion-header>

	<ion-content>
		<GPullRefresh @refresh="handleRefresh" />

		<!-- tabindex="0" so a keyboard can reach the scroll. axe's
		     scrollable-region-focusable fires when a scrollable box has no
		     focusable child — which happens exactly when the list is EMPTY, so it
		     only surfaced once the empty state stopped carrying a button. A
		     keyboard user could not scroll the region at all. -->
		<div
			class="flex flex-col items-center mb-7 p-4 h-full w-full sm:max-w-2xl sm:mx-auto overflow-y-auto"
			ref="scrollContainer"
			tabindex="0"
			:aria-label="pageTitle"
			@scroll="() => handleScroll()"
		>
			<div class="w-full">
				<GSegmented
					v-if="props.tabButtons"
					class="mt-5"
					:buttons="props.tabButtons"
					v-model="activeTab"
					:label="__('Filter list')"
				/>

				<!-- §15.1: ONE glass panel for the whole list, not one surface per
				     row. §11.2: skeleton rows mirroring the real row shape while
				     loading — the LoadingIndicator spinner this replaces is one of
				     the seven §11.2 names. -->
				<GListPanel
					v-if="documents.loading || documents.data?.length"
					class="mt-5"
					:loading="documents.loading"
					:rows="4"
				>
					<div
						class="g-listview__row"
						v-for="link in documents.data"
						:key="link.name"
					>
						<component
							v-if="props.doctype === 'Employee Checkin'"
							:is="listItemComponent[doctype]"
							:doc="link"
							:isTeamRequest="isTeamRequest"
							:workflowStateField="workflowStateField"
							@click="openRequestModal(link)"
						/>
						<router-link
							v-else
							:to="{ name: detailViewRoute, params: { id: link.name } }"
							v-slot="{ navigate }"
						>
							<component
								:is="listItemComponent[doctype]"
								:doc="link"
								:isTeamRequest="isTeamRequest"
								:workflowStateField="workflowStateField"
								@click="navigate"
							/>
						</router-link>
					</div>
				</GListPanel>

				<ResourceError
					v-else-if="documents.error"
					:resource="documents"
					:what="props.doctype?.toLowerCase()"
				/>

				<!-- §11.1: an empty screen is an invitation to act. The copy is per
				     list, never "no records found" and never a generic doctype
				     string. -->
				<!-- §11.1 says always say what to do. Three of these bodies said
				     "Claim it here" / "claim it here" / "Claim the time back here"
				     with nothing in the box to tap — "here" pointed at a button in
				     the header, if it pointed anywhere. Same route as that button,
				     shown only when the user may actually create one. -->
				<!-- No action here (§18, v1.11). 8.11 put a create button in this
				     slot because three of the copies promised one; the header's
				     create action is now a GButton too, so an action here made
				     "New" appear twice on the same screen. The copy references it
				     instead. -->
				<GEmptyState
					v-else
					class="mt-5"
					:title="emptyCopy.title"
					:body="emptyCopy.body"
				/>
			</div>
		</div>

		<GModal trigger="show-filter-modal">
			<!-- Filter Action Sheet -->
			<template #actionSheet>
				<ListFiltersActionSheet
					:filterConfig="filterConfig"
					@applyFilters="applyFilters"
					@clearFilters="clearFilters"
					v-model:filters="filterMap"
				/>
			</template>
		</GModal>
	</ion-content>

	<GModal :is-open="isRequestModalOpen" @did-dismiss="closeRequestModal">
		<RequestActionSheet
			:fields="EMPLOYEE_CHECKIN_FIELDS"
			:showOpenForm="false"
			v-model="selectedRequest"
		/>
	</GModal>
</template>

<script setup>
import GButton from "@/components/glass/GButton.vue"
import GIconButton from "@/components/glass/GIconButton.vue"
import GModal from "@/components/glass/GModal.vue"
import GSegmented from "@/components/glass/GSegmented.vue"
import GPullRefresh from "@/components/glass/GPullRefresh.vue"
import GEmptyState from "@/components/glass/GEmptyState.vue"
import GListPanel from "@/components/glass/GListPanel.vue"
import { useRouter } from "vue-router"
import { inject, ref, markRaw, watch, computed, reactive, onMounted } from "vue"
import {
	modalController,
	IonHeader,
	IonContent,
} from "@ionic/vue"

import { FeatherIcon, createResource, debounce } from "frappe-ui"

import EmployeeCheckinItem from "@/components/EmployeeCheckinItem.vue"
import AttendanceRequestItem from "@/components/AttendanceRequestItem.vue"
import ShiftRequestItem from "@/components/ShiftRequestItem.vue"
import ShiftAssignmentItem from "@/components/ShiftAssignmentItem.vue"
import LeaveRequestItem from "@/components/LeaveRequestItem.vue"
import ExpenseClaimItem from "@/components/ExpenseClaimItem.vue"
import ListFiltersActionSheet from "@/components/ListFiltersActionSheet.vue"
import RequestActionSheet from "@/components/RequestActionSheet.vue"
import { EMPLOYEE_CHECKIN_FIELDS } from "@/data/config/requestSummaryFields"

import useWorkflow from "@/composables/workflow"
import { useListUpdate } from "@/composables/realtime"

const __ = inject("$translate")
const props = defineProps({
	doctype: {
		type: String,
		required: true,
	},
	fields: {
		type: Array,
		required: true,
	},
	groupBy: {
		type: String,
		required: false,
	},
	filterConfig: {
		type: Array,
		required: true,
	},
	tabButtons: {
		type: Array,
		required: false,
	},
	pageTitle: {
		type: String,
		required: true,
	},
})

// §11.1 — an empty screen is an invitation to act: say what to do, never
// "no records found", never a generic doctype string. Three of these are the
// spec's own words (leave, overtime, issues); the other six are written in the
// same voice and recorded back into §11.1, because the table covers only the
// screens the mockup drew.
const EMPTY_COPY = {
	"Leave Application": {
		title: __("No leave taken this year"),
		body: __("Your applications will appear here once submitted"),
	},
	"OT Request": {
		title: __("No overtime claims yet"),
		body: __("Stay past your shift end, punch out, then use New above"),
	},
	"Employee Issue": {
		title: __("Nothing reported"),
		body: __("If something looks wrong, tell us — a screenshot helps"),
	},
	"Attendance Request": {
		title: __("No attendance requests yet"),
		body: __("Ask for a day to be corrected and it will appear here"),
	},
	"Shift Request": {
		title: __("No shift requests yet"),
		body: __("Ask to work a different shift and it will appear here"),
	},
	"Shift Assignment": {
		title: __("No shifts assigned yet"),
		body: __("Your roster appears here once your manager publishes it"),
	},
	"Employee Checkin": {
		title: __("No check-ins recorded"),
		body: __("Punch in from Home and your record appears here"),
	},
	"Expense Claim": {
		title: __("No expense claims yet"),
		body: __("Paid for something for work? Use New above to claim it"),
	},
	"Replacement Leave Claim": {
		title: __("No replacement leave claimed"),
		body: __("Worked a rest day? Use New above to claim the time back"),
	},
}

const emptyCopy = computed(
	() =>
		EMPTY_COPY[props.doctype] ?? {
			title: __("Nothing here yet"),
			body: __("New records will appear here once they are created"),
		}
)


const getButtonKey = (tab) => tab?.key ?? tab

const listItemComponent = {
	"Employee Checkin": markRaw(EmployeeCheckinItem),
	"Attendance Request": markRaw(AttendanceRequestItem),
	"Shift Request": markRaw(ShiftRequestItem),
	"Shift Assignment": markRaw(ShiftAssignmentItem),
	"Leave Application": markRaw(LeaveRequestItem),
	"Expense Claim": markRaw(ExpenseClaimItem),
}

const router = useRouter()
const dayjs = inject("$dayjs")
const socket = inject("$socket")
const employee = inject("$employee")
const filterMap = reactive({})
const activeTab = ref(props.tabButtons ? getButtonKey(props.tabButtons[0]) : undefined)
const areFiltersApplied = ref(false)
const appliedFilters = ref([])
const workflowStateField = ref(null)
const isRequestModalOpen = ref(false)
const selectedRequest = ref(null)

// infinite scroll
const scrollContainer = ref(null)
const hasNextPage = ref(true)
const listOptions = ref({
	doctype: props.doctype,
	fields: props.fields,
	group_by: props.groupBy,
	order_by: `\`tab${props.doctype}\`.modified desc`,
	page_length: 50,
})

// computed properties
const isTeamRequest = computed(() => {
	return props.tabButtons && activeTab.value === getButtonKey(props.tabButtons[1])
})

const formViewRoute = computed(() => {
	return `${props.doctype.replace(/\s+/g, "")}FormView`
})

const detailViewRoute = computed(() => {
	return `${props.doctype.replace(/\s+/g, "")}DetailView`
})

const defaultFilters = computed(() => {
	const filters = []

	if (isTeamRequest.value) {
		filters.push([props.doctype, "employee", "!=", employee.data.name])
	} else {
		filters.push([props.doctype, "employee", "=", employee.data.name])
	}

	return filters
})

// resources
const documents = createResource({
	url: "frappe.desk.reportview.get",
	onSuccess: (data) => {
		if (data.values?.length < listOptions.value.page_length) {
			hasNextPage.value = false
		}
	},
	transform(data) {
		if (data.length === 0) {
			return []
		}

		// convert keys and values arrays to docs object
		const fields = data["keys"]
		const values = data["values"]
		const docs = values.map((value) => {
			const doc = {}
			fields.forEach((field, index) => {
				doc[field] = value[index]
			})
			return doc
		})

		let pagedData
		if (!documents.params.start || documents.params.start === 0) {
			pagedData = docs
		} else {
			pagedData = documents.data.concat(docs)
		}

		return pagedData
	},
})

const createPermission = createResource({
	url: "frappe.client.has_permission",
	// Frappe's Pydantic-validated handler rejects `docname: null` — pass an
	// empty string for the "do I have create perm at all" probe.
	params: { doctype: props.doctype, docname: "", perm_type: "create" },
	auto: true,
})

// helper functions
const openRequestModal = async (request) => {
	selectedRequest.value = request
	selectedRequest.value.doctype = "Employee Checkin"
	selectedRequest.value.date = request.time
	selectedRequest.value.formatted_time = dayjs(request.time).format("HH:mm a")
	selectedRequest.value.formatted_latitude = `${Number(request.latitude).toFixed(5)}°`
	selectedRequest.value.formatted_longitude = `${Number(request.longitude).toFixed(5)}°`
	isRequestModalOpen.value = true
}

const closeRequestModal = async () => {
	isRequestModalOpen.value = false
	selectedRequest.value = null
}

function initializeFilters() {
	props.filterConfig.forEach((filter) => {
		filterMap[filter.fieldname] = {
			condition: "=",
			value: null,
		}
	})

	appliedFilters.value = []
}
initializeFilters()

function prepareFilters() {
	let condition = ""
	let value = ""
	appliedFilters.value = []

	for (const fieldname in filterMap) {
		condition = filterMap[fieldname].condition
		// accessing .value because autocomplete returns an object instead of value
		if (typeof condition === "object" && condition !== null) {
			condition = condition.value
		}

		value = filterMap[fieldname].value
		if (condition && value) appliedFilters.value.push([props.doctype, fieldname, condition, value])
	}
}

function applyFilters() {
	prepareFilters()
	fetchDocumentList()
	modalController.dismiss()
	areFiltersApplied.value = appliedFilters.value.length ? true : false
}

function clearFilters() {
	initializeFilters()
	fetchDocumentList()
	modalController.dismiss()
	areFiltersApplied.value = false
}

function fetchDocumentList(start = 0) {
	if (start === 0) {
		hasNextPage.value = true
	}

	const filters = [[props.doctype, "docstatus", "!=", "2"]]
	filters.push(...defaultFilters.value)

	if (appliedFilters.value) filters.push(...appliedFilters.value)

	if (workflowStateField.value) {
		listOptions.value.fields.push(workflowStateField.value)
	}

	documents.submit({
		...listOptions.value,
		start: start || 0,
		filters: filters,
	})
}

const handleScroll = debounce(() => {
	if (!hasNextPage.value) return

	const { scrollTop, scrollHeight, clientHeight } = scrollContainer.value
	const scrollPercentage = (scrollTop / (scrollHeight - clientHeight)) * 100

	if (scrollPercentage >= 90) {
		const start = documents.params.start + listOptions.value.page_length
		fetchDocumentList(start)
	}
}, 500)

const handleRefresh = (event) => {
	setTimeout(() => {
		fetchDocumentList()
		event.target.complete()
	}, 500)
}

watch(
	() => activeTab.value,
	(_value) => {
		fetchDocumentList()
	}
)

onMounted(async () => {
	// BEFORE the await: Vue unsets the component instance at an async hook's
	// first await, so a useListUpdate call after it would find
	// getCurrentInstance() null and its onBeforeUnmount teardown would never
	// register — this exact line leaked one permanent handler per mount.
	useListUpdate(socket, props.doctype, () => fetchDocumentList())

	const workflow = useWorkflow(props.doctype)
	await workflow.workflowDoc.promise
	workflowStateField.value = workflow.getWorkflowStateField()
	fetchDocumentList()
})
</script>

<style scoped>
ion-content {
	--background: var(--g-bg);
}
</style>
