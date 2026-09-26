<template>
	<!-- The one header (alpha.5). This list drew its own bar with a 2px
	     hairline and Back via router.back(), which did nothing on a page opened
	     cold; ShellHeader's Back is goBackOrHome. Filter and New are this
	     screen's own actions, so they take the bell/avatar slot. -->
	<ShellHeader :title="pageTitle">
		<template #actions>
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
				<Funnel class="h-5 w-5" aria-hidden="true" />
			</GIconButton>
			<router-link
				v-if="canCreate"
				:to="{ name: formViewRoute }"
				v-slot="{ navigate }"
				class="shrink-0"
			>
				<!-- "New" is a round + bar button, as in iOS (alpha.7 A8/A9);
				     lime is kept for the one primary action on a screen. -->
				<GIconButton :label="__('New', null, props.doctype)" @click="navigate">
					<Plus class="h-5 w-5" aria-hidden="true" />
				</GIconButton>
			</router-link>
		</template>
	</ShellHeader>

	<ion-content
		ref="content"
		class="g-page__content"
		:scroll-events="true"
		@ionScroll="handleScroll"
	>
		<GPullRefresh @refresh="handleRefresh" />

		<!-- tabindex="0" so a keyboard can reach the scroll. axe's
		     scrollable-region-focusable fires when a scrollable box has no
		     focusable child — which happens exactly when the list is EMPTY, so it
		     only surfaced once the empty state stopped carrying a button. A
		     keyboard user could not scroll the region at all. -->
		<!-- The one content column (§20.3): 720px, left-aligned against the side
		     nav at lg:. It was sm:max-w-2xl (672px) centred — a second width. -->
		<!-- One scroller: ion-content's (alpha.8 r3). A second overflow box
		     here scrolled every list 28 px past its content. -->
		<div
			class="flex flex-col items-center p-4 w-full max-w-content-column-lg mx-auto"
			:aria-label="pageTitle"
		>
			<div class="w-full">
				<GSegmented
					v-if="props.tabButtons"
					class="mt-5"
					:buttons="props.tabButtons"
					v-model="activeTab"
					:label="__('Filter list')"
					@update:model-value="tabChosenByHand = true"
				/>

				<!-- §15.1: ONE glass panel for the whole list, not one surface per
				     row. §11.2: skeleton rows mirroring the real row shape while
				     loading — the LoadingIndicator spinner this replaces is one of
				     the seven §11.2 names. -->
				<!-- Check-ins: one group per day under a day heading (alpha.7 0.8,
				     iOS lists), not the day repeated on every row. -->
				<template v-if="props.doctype === 'Employee Checkin' && documents.data?.length">
					<section
						v-for="group in checkinDays"
						:key="group.day"
						class="g-form-section g-checkin-day mt-5"
					>
						<h2 class="g-form-section__title">{{ __(dayHeading(group.day, today)) }}</h2>
						<div class="g-form-group">
							<EmployeeCheckinItem
								v-for="link in group.rows"
								:key="link.name"
								:doc="link"
								@click="openRequestModal(link)"
							/>
						</div>
					</section>
				</template>
				<GListPanel
					v-else-if="documents.loading || documents.data?.length"
					class="mt-5"
					:loading="documents.loading"
					:rows="4"
				>
					<div class="g-listview__row" v-for="link in documents.data" :key="link.name">
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
					:what="listNoun"
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
				<!-- Only after the list really answered: before that (or when the
				     request never ran) "No … yet" would be a false statement. -->
				<GEmptyState
					v-else-if="listAnswered"
					class="mt-5"
					:icon="EMPTY_ICON[props.doctype]"
					:title="emptyCopy.title"
					:body="emptyCopy.body"
				/>
			</div>
		</div>

		<GModal trigger="show-filter-modal" :title="__('Filters')">
			<template #confirm>
				<button type="button" class="g-sheet__done g-focusable" @click="applyFilters">
					{{ __("Done") }}
				</button>
			</template>
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
import {
	CalendarCheck,
	CalendarClock,
	Clock,
	Funnel,
	MapPin,
	Palmtree,
	Plus,
	Receipt,
} from "lucide-vue-next"
import { IonContent, modalController } from "@ionic/vue"
import ShellHeader from "@/components/ShellHeader.vue"
import { createResource, debounce } from "frappe-ui"
import { computed, inject, markRaw, onMounted, reactive, ref, watch } from "vue"
import { initialListTab } from "@/utils/listTab"
import { filterCondition } from "@/utils/listFilters"
import { dayHeading, groupByDay, workDayOf } from "@/utils/dayGroups"
import { siteTime, siteTimeZone } from "@/utils/siteTime"
import { useRoute, useRouter } from "vue-router"
import AttendanceRequestItem from "@/components/AttendanceRequestItem.vue"
import EmployeeCheckinItem from "@/components/EmployeeCheckinItem.vue"
import ExpenseClaimItem from "@/components/ExpenseClaimItem.vue"
import GEmptyState from "@/components/glass/GEmptyState.vue"
import { REQUEST_KIND } from "@/utils/requestKind"
import GIconButton from "@/components/glass/GIconButton.vue"
import GListPanel from "@/components/glass/GListPanel.vue"
import GModal from "@/components/glass/GModal.vue"
import GPullRefresh from "@/components/glass/GPullRefresh.vue"
import GSegmented from "@/components/glass/GSegmented.vue"
import LeaveRequestItem from "@/components/LeaveRequestItem.vue"
import ListFiltersActionSheet from "@/components/ListFiltersActionSheet.vue"
import OTRequestItem from "@/components/OTRequestItem.vue"
import ReplacementLeaveClaimItem from "@/components/ReplacementLeaveClaimItem.vue"
import RequestActionSheet from "@/components/RequestActionSheet.vue"
import ShiftAssignmentItem from "@/components/ShiftAssignmentItem.vue"
import ShiftRequestItem from "@/components/ShiftRequestItem.vue"
import { useListUpdate } from "@/composables/realtime"

import useWorkflow from "@/composables/workflow"
import { EMPLOYEE_CHECKIN_FIELDS } from "@/data/config/requestSummaryFields"

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
	// Field + direction to sort by, e.g. "time desc". Defaults to creation desc:
	// newest request first, in the order they were asked (alpha.12 Q1). It was
	// modified desc, so an old request an approver touched jumped to the top.
	// Employee Checkin history sorts by the PUNCH time, for the same reason.
	orderBy: {
		type: String,
		required: false,
		default: "creation desc",
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
		body: __("Time off you ask for shows up here."),
	},
	"OT Request": {
		title: __("No overtime claims yet"),
		body: __("Stay past your shift end, check out, then tap New"),
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
		body: __("Check in from Home and your record appears here"),
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

//: The kind's own symbol on its empty list (alpha.7 §5.3), the same one the
//: New request sheet and Needs you use.
const EMPTY_ICON = {
	"Leave Application": markRaw(Palmtree),
	"OT Request": markRaw(Clock),
	"Expense Claim": markRaw(Receipt),
	"Shift Request": markRaw(CalendarClock),
	"Attendance Request": markRaw(CalendarCheck),
	"Employee Checkin": markRaw(MapPin),
	"Shift Assignment": markRaw(CalendarClock),
}

const getButtonKey = (tab) => tab?.key ?? tab

const listItemComponent = {
	"Employee Checkin": markRaw(EmployeeCheckinItem),
	"Attendance Request": markRaw(AttendanceRequestItem),
	"Shift Request": markRaw(ShiftRequestItem),
	"Shift Assignment": markRaw(ShiftAssignmentItem),
	"Leave Application": markRaw(LeaveRequestItem),
	"Expense Claim": markRaw(ExpenseClaimItem),
	// Both were missing: the rows were fetched and `<component :is="undefined">`
	// rendered every one of them blank.
	"OT Request": markRaw(OTRequestItem),
	"Replacement Leave Claim": markRaw(ReplacementLeaveClaimItem),
}

const router = useRouter()
const dayjs = inject("$dayjs")
const socket = inject("$socket")
const employee = inject("$employee")
const filterMap = reactive({})
const route = useRoute()
// ?tab=team opens the approver's tab (audit P0-9). The team tab only exists
// once the approver check has loaded, so the pick is re-made when the tabs
// change, until the person picks a tab themselves.
const activeTab = ref(initialListTab(props.tabButtons, route.query.tab))
let tabChosenByHand = false
watch(
	() => props.tabButtons,
	(tabs) => {
		if (!tabChosenByHand) activeTab.value = initialListTab(tabs, route.query.tab)
	}
)
const areFiltersApplied = ref(false)
const appliedFilters = ref([])
const workflowStateField = ref(null)
const isRequestModalOpen = ref(false)
const selectedRequest = ref(null)

// infinite scroll, read from ion-content's own scroller
const content = ref(null)
const hasNextPage = ref(true)
const listOptions = ref({
	doctype: props.doctype,
	// copy, don't alias: fetchDocumentList pushes the workflow-state field into
	// this array, and sharing the prop's reference mutated the parent AND grew
	// the query by a duplicate column on every fetch (mount, filter, paginate,
	// pull-refresh, realtime).
	fields: [...props.fields],
	group_by: props.groupBy,
	order_by: `\`tab${props.doctype}\`.${props.orderBy}`,
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

//: Check-ins by their WORK day on the site clock (alpha.7 0.8; alpha.11: a
//: check-out after midnight sits under the day it closed, not alone under the
//: next one).
const today = dayjs().tz(siteTimeZone()).format("YYYY-MM-DD")
const checkinDays = computed(() => groupByDay(documents.data, workDayOf(documents.data, siteTime)))

//: The list request finished with an answer (possibly an empty one).
const listAnswered = computed(() => Array.isArray(documents.data))

//: What failed, in the words the screen uses ("your time off"), never the
//: doctype ("leave application"): the plain-words rule W1.
const listNoun = computed(() => {
	const other = { "Employee Checkin": "your check-ins", "Shift Assignment": "your shifts" }
	if (other[props.doctype]) return __(other[props.doctype])
	const kind = REQUEST_KIND[props.doctype]
	return kind ? __("your {0} requests", [__(kind).toLowerCase()]) : __("this list")
})

const createPermission = createResource({
	url: "frappe.client.has_permission",
	// Frappe's Pydantic-validated handler rejects `docname: null` — pass an
	// empty string for the "do I have create perm at all" probe.
	params: { doctype: props.doctype, docname: "", perm_type: "create" },
	auto: true,
})

// Show "New" only when the create route actually exists. Some doctypes
// (Shift Assignment, Employee Checkin) are read-only in the app on purpose and
// have no FormView route; without this guard the button rendered from the
// backend create permission and its tap resolved no route — a dead control.
const canCreate = computed(
	() =>
		createPermission?.data?.has_permission &&
		props.doctype !== "Employee Checkin" &&
		router.hasRoute(formViewRoute.value)
)

// helper functions

// A check-in captured with tracking off (or an older row) has null / 0 /
// missing coordinates: Number(undefined).toFixed(5) rendered a literal "NaN°"
// and Number(null) a misleading "0.00000°". Show an em dash for anything that
// isn't a real reading.
const formatCoord = (v) => {
	const n = Number(v)
	return Number.isFinite(n) && n !== 0 ? `${n.toFixed(5)}°` : "—"
}

const openRequestModal = async (request) => {
	selectedRequest.value = request
	selectedRequest.value.doctype = "Employee Checkin"
	selectedRequest.value.date = request.time
	selectedRequest.value.formatted_time = dayjs(request.time).format("h:mm a")
	selectedRequest.value.formatted_latitude = formatCoord(request.latitude)
	selectedRequest.value.formatted_longitude = formatCoord(request.longitude)
	isRequestModalOpen.value = true
}

const closeRequestModal = async () => {
	isRequestModalOpen.value = false
	selectedRequest.value = null
}

function initializeFilters() {
	props.filterConfig.forEach((filter) => {
		filterMap[filter.fieldname] = {
			condition: filterCondition(filter),
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

	if (workflowStateField.value && !listOptions.value.fields.includes(workflowStateField.value)) {
		listOptions.value.fields.push(workflowStateField.value)
	}

	documents.submit({
		...listOptions.value,
		start: start || 0,
		filters: filters,
	})
}

const handleScroll = debounce(async () => {
	if (!hasNextPage.value) return

	const scroller = await content.value?.$el?.getScrollElement?.()
	if (!scroller) return
	const { scrollTop, scrollHeight, clientHeight } = scroller
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

	// The workflow only names an extra column. A failed lookup must not stop
	// the list request, or the screen falls through to "No … yet" as if the
	// person had no records (alpha.12 C2, measured with forced 500s).
	const workflow = useWorkflow(props.doctype)
	try {
		await workflow.workflowDoc.promise
		workflowStateField.value = workflow.getWorkflowStateField()
	} catch (error) {
		console.warn("[ListView] workflow lookup failed; listing without it:", props.doctype, error)
	}
	fetchDocumentList()
})
</script>

<style scoped>
ion-content {
	--background: var(--g-bg);
}
</style>
