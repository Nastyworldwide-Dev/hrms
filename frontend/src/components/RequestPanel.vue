<template>
	<div class="w-full">
		<GSegmented :buttons="TAB_BUTTONS" v-model="activeTab" :label="__('Requests')" />
		<p v-if="refreshing" class="text-xs text-ink-500 mt-2" role="status">
			{{ __("Refreshing…") }}
		</p>
		<!-- FILTER CHIPS (mockup 4 gap #3). The question somebody brings to this
		     screen is almost always one of three: what is still out, what came
		     back yes, what came back no. A list with no filter is a list you
		     scroll.

		     `aria-pressed` toggles in a group, NOT role="tab": these do not move
		     between panels, they narrow one list — the distinction mockup 4's
		     own notes make and the reason its nav is aria-current. -->
		<div class="g-chips" role="group" :aria-label="__('Filter requests')">
			<button
				v-for="chip in FILTERS"
				:key="chip.key"
				type="button"
				class="g-chip g-focusable"
				:class="{ 'g-chip--on': filter === chip.key }"
				:aria-pressed="filter === chip.key"
				@click="filter = chip.key"
			>
				{{ __(chip.label) }}
				<span v-if="filterCounts[chip.key]" class="g-chip__count">{{
					filterCounts[chip.key]
				}}</span>
			</button>
		</div>

		<div ref="listRegion" id="request-panel-list" tabindex="-1" class="g-focusable">
			<!-- TWO PILES while the filter is ALL (mockup 4 gap #2): work in
			     flight, then the record. Mixing them makes the reader sort by
			     eye on every open. -->
			<template v-if="splitting">
				<template v-if="waitingGroup.length">
					<div class="g-eyebrow mt-4 mb-2">{{ __("Waiting on someone") }}</div>
					<RequestList
						:items="waitingGroup"
						:teamRequests="activeTab !== 'mine'"
						v-bind="emptyCopy"
					/>
				</template>
				<template v-if="finishedGroup.length">
					<div class="g-eyebrow mt-4 mb-2">{{ __("Finished") }}</div>
					<RequestList
						:items="finishedGroup"
						:teamRequests="activeTab !== 'mine'"
						v-bind="emptyCopy"
					/>
				</template>
				<RequestList
					v-if="!waitingGroup.length && !finishedGroup.length"
					:items="shown"
					:teamRequests="activeTab !== 'mine'"
					v-bind="emptyCopy"
				/>
			</template>
			<RequestList v-else :items="shown" :teamRequests="activeTab !== 'mine'" v-bind="emptyCopy" />
		</div>
		<p class="sr-only" role="status">{{ revealed }}</p>

		<!-- Not a GGhostButton: that is a glass surface and Home already spends
		     4 of its 6 (§15.1). A text control under a list costs none, and the
		     row it reveals is the one the person came for.
		     min-h, not padding arithmetic: py-3 + text-sm computes to exactly
		     44px, which is §14's floor met by luck and one utility away from
		     failing — and at 120% dynamic type the label grows while the
		     padding does not. The list row (§10.1 #3) guards the same floor
		     with an explicit minimum; so does this — through the token that
		     defines the floor (--g-touch-target-min), not a literal 44px, so
		     one value governs every target in the app. -->
		<button
			v-if="hidden > 0"
			type="button"
			class="g-focusable g-list-more w-full py-3 text-sm text-ink-600 bg-transparent border-none"
			aria-expanded="false"
			aria-controls="request-panel-list"
			@click="expand"
		>
			{{ __("Show {0} more", [hidden]) }}
		</button>
	</div>
</template>

<script setup>
import { ref, inject, onMounted, computed, markRaw, watch, nextTick } from "vue"
import { useRoute } from "vue-router"

import GSegmented from "@/components/glass/GSegmented.vue"
import RequestList from "@/components/RequestList.vue"
import { myRequestCounts } from "@/data/requestCounts"
import { requestStatus } from "@/utils/requestStatus"

import { historyShiftRequests, myAttendanceRequests, myShiftRequests } from "@/data/attendance"
import { historyClaims, myClaims } from "@/data/claims"
import { historyLeaves, myLeaves } from "@/data/leaves"
import { isApprover } from "@/data/team"
import { myOTRequests, myReplacementLeaveClaims } from "@/data/overtime"

import AttendanceRequestItem from "@/components/AttendanceRequestItem.vue"
import ExpenseClaimItem from "@/components/ExpenseClaimItem.vue"
import LeaveRequestItem from "@/components/LeaveRequestItem.vue"
import ShiftRequestItem from "@/components/ShiftRequestItem.vue"
import OTRequestItem from "@/components/OTRequestItem.vue"
import ReplacementLeaveClaimItem from "@/components/ReplacementLeaveClaimItem.vue"

import { useListUpdate, useReloadOnGap } from "@/composables/realtime"
import {
	MY_REQUEST_LISTS,
	REQUEST_LISTS,
	reloadLists,
	reloadRequestLists,
} from "@/data/requestLists"
import { siteTime } from "@/utils/siteTime"

const HISTORY_LISTS = [historyLeaves, historyClaims, historyShiftRequests]
const route = useRoute()
//: ?tab=answered opens what the approver already decided (Approvals links it).
const activeTab = ref(route.query.tab === "answered" ? "answered" : "mine")

// Home shows the first five of whatever the active tab holds, and a control
// that reveals the rest in place. The fold is a budget, not a length
// (home-fold-budget.test.js): the ANCHOR above this panel fits the smallest
// usable height and this list is scrolled to by design — what the cap removes
// is an UNBOUNDED scroll, not the scroll.
//
// CORRECTED after design review. The commit that added this said "a row is
// two lines, ~62px, so five is ~310px inside the ~440px budget". That was
// measured on MY REQUESTS only. A team row carries a third line — ListItem
// renders an avatar and the employee name under `isTeamRequest` — so:
//     own rows  ~70px  ->  5 = ~348px
//     team rows ~102px ->  5 = ~508px, past the small-phone budget on its own
// Five stays, and the cap is the same on every tab, because this panel is
// BELOW the anchor and is scrolled to either way: what five buys is a bound,
// not a fit. One cap for three tabs is also the thing a person can predict.
// The number to revisit if this panel ever moves above the fold is this one.
//
// Expanding, not linking: each tab merges SIX doctypes and there is no
// combined list route, so "See all (9)" could only point at one type's screen
// and answer a tap about nine requests with a page showing three.
const HOME_ROWS = 5
const showAll = ref(false)
const listRegion = ref(null)
const revealed = ref("")

// The button renders `v-if="hidden > 0"`, so activating it unmounts the very
// element that had focus and focus falls back to <body> — a keyboard or
// screen-reader user presses Enter, rows appear, and they are returned to the
// top of the page with no idea where they were. So the list takes focus, and
// a polite live region says what happened; the control's own disappearance is
// the one thing that cannot announce it (design review of 70bffe660).
async function expand() {
	const count = hidden.value
	showAll.value = true
	revealed.value = __("{0} more requests shown", [count])
	await nextTick()
	listRegion.value?.focus()
}
const socket = inject("$socket")
const __ = inject("$translate")

// What waits on an approver lives on Approvals (AUDIT-PLAN Approvals row),
// so there is no team tab here any more. What they already
// decided stays reachable, worded for what is behind it (ruling 2).
const MINE = { key: "mine", label: __("My requests") }
//: Short on the pill so it fits one line at 360; the door on Approvals
//: carries the full words, "Requests you've already answered".
const ANSWERED = { key: "answered", label: __("Answered by you") }
const TAB_BUTTONS = computed(() => (isApprover.data ? [MINE, ANSWERED] : [MINE]))

// The cached isApprover verdict hydrates async and can flip true -> false
// after paint; without this clamp a user parked on a vanished tab renders an
// empty panel (no v-if branch matches).
watch(TAB_BUTTONS, (tabs) => {
	if (!tabs.map((tab) => tab.key).includes(activeTab.value)) {
		console.info("[RequestPanel] active tab vanished, falling back:", activeTab.value)
		activeTab.value = "mine"
	}
})

// A cached (IndexedDB) paint can show last session's status until the first
// fetch of this session answers; say so instead of painting it as current.
const refreshing = computed(() =>
	(activeTab.value === "mine" ? MY_REQUEST_LISTS : HISTORY_LISTS).some(
		(list) => !list.fetched && !list.error
	)
)

const myRequests = computed(() =>
	updateRequestDetails(
		myLeaves,
		myClaims,
		myShiftRequests,
		myAttendanceRequests,
		myOTRequests,
		myReplacementLeaveClaims
	)
)

// Attendance Request, OT Request and Replacement Leave Claim are all
// docstatus-driven (no status/approver field), so the history trail — which is
// "decided, and I was the named approver" — covers leaves, claims and shift
// requests only.
const historyRequests = computed(() =>
	updateRequestDetails(historyLeaves, historyClaims, historyShiftRequests, null, null, null)
)

//: One line saying what is missing (ruling 2), per tab.
const emptyCopy = computed(() =>
	activeTab.value === "answered"
		? { emptyStateTitle: __("You haven't answered any requests yet."), emptyStateMessage: " " }
		: {}
)

const unfiltered = computed(() => {
	if (activeTab.value === "answered") return historyRequests.value
	return myRequests.value
})

//: FILTER CHIPS (mockup 4 gap #3). A list with no filter is a list you scroll,
//: and the question an employee brings to this screen is almost always one of
//: three: what is still out, what came back yes, what came back no.
//:
//: Derived from `requestStatus`, the same helper the chip on each row reads, so
//: a filter can never disagree with the label beside it — which is how
//: "Pending", "Open" and "Draft" came to mean one thing on three screens.
const FILTERS = [
	{ key: "all", label: "All" },
	{ key: "waiting", label: "Waiting" },
	{ key: "approved", label: "Approved" },
	{ key: "rejected", label: "Not approved" },
]
const filter = ref("all")

function verdictOf(request) {
	return requestStatus(request.doctype, request)
}

//: PURE, and takes the key rather than reading the ref. The first version
//: swapped `filter.value` to count each chip and put it back — a side effect
//: inside a computed, which eslint caught and which would have made the
//: displayed list flicker through three filters on every recount.
function matches(request, key) {
	if (key === "all") return true
	const verdict = verdictOf(request)
	if (key === "waiting") return verdict.pending
	if (verdict.pending) return false
	// A decided request is one or the other. Matched on the LABEL rather than
	// on docstatus, because in this app a rejection is submitted exactly like
	// an approval — the decision lives in the field, not the docstatus.
	const decided = String(verdict.label || "").toLowerCase()
	if (key === "rejected") return decided.includes("reject")
	return !decided.includes("reject") && !decided.includes("cancel")
}

//: How many each chip would show. A chip that opens an empty list is a tap
//: nobody should have to spend to find that out.
const filterCounts = computed(() => {
	// My own requests: the server counts every one of them (audit P0-8). The
	// Team and History tabs keep the loaded-row count until the Approvals page.
	if (activeTab.value === "mine" && myRequestCounts.data) return myRequestCounts.data
	const counts = {}
	for (const { key } of FILTERS) {
		counts[key] = unfiltered.value.filter((request) => matches(request, key)).length
	}
	return counts
})

const activeRequests = computed(() =>
	unfiltered.value.filter((request) => matches(request, filter.value))
)

const shown = computed(() =>
	showAll.value ? activeRequests.value : activeRequests.value.slice(0, HOME_ROWS)
)

//: TWO PILES, not one list (mockup 4 gap #2). "Waiting on someone" is work in
//: flight and "Finished" is a record — different jobs, and mixing them makes
//: the reader sort by eye on every open.
//:
//: Only while the filter is ALL. Once somebody has asked for just the waiting
//: ones, a heading over the only group there is adds a line and no meaning.
//:
//: DECLARED AFTER `shown`, which it reads. A computed's getter is lazy, so
//: this happened to work — and the script-setup order gate refuses it anyway,
//: rightly: the moment anything makes one of these eager the screen throws
//: "before initialization" and Ionic is left holding a view with no element.
//: Third instance of that class today.
function verdictPending(request) {
	return verdictOf(request).pending
}

const splitting = computed(() => filter.value === "all")
const waitingGroup = computed(() => (splitting.value ? shown.value.filter(verdictPending) : []))
const finishedGroup = computed(() =>
	splitting.value ? shown.value.filter((request) => !verdictPending(request)) : []
)

// What is HIDDEN, not what exists: a person with seven requests told "Show 7
// more" taps it and finds two new rows.
const hidden = computed(() =>
	showAll.value ? 0 : Math.max(0, activeRequests.value.length - HOME_ROWS)
)

// The tab strip swaps the list under the control. A stale `showAll` would open
// the next tab already expanded, which is the opposite of what the cap is for.
watch(activeTab, () => {
	showAll.value = false
	revealed.value = ""
	// The filter belongs to the list it narrowed. Carrying "Not approved" into
	// the Team tab opens it on an empty list that looks broken.
	filter.value = "all"
})

function updateRequestDetails(
	leaves,
	claims,
	shiftRequests,
	attendanceRequests,
	otRequests,
	replacementLeaveClaims
) {
	const requests = [
		leaves,
		claims,
		shiftRequests,
		attendanceRequests,
		otRequests,
		replacementLeaveClaims,
	].reduce((acc, resource) => acc.concat(resource?.data || []), [])

	const componentMap = {
		"Leave Application": LeaveRequestItem,
		"Expense Claim": ExpenseClaimItem,
		"Shift Request": ShiftRequestItem,
		"Attendance Request": AttendanceRequestItem,
		"OT Request": OTRequestItem,
		"Replacement Leave Claim": ReplacementLeaveClaimItem,
	}
	requests.forEach((request) => {
		request.component = markRaw(componentMap[request.doctype])
	})

	return getSortedRequests(requests)
}

function getSortedRequests(list) {
	// return top 10 requests sorted by posting date
	return list
		.sort((a, b) => {
			// site-clock strings; the Date constructor rejects them on Safari (I-F3)
			return siteTime(b.creation).valueOf() - siteTime(a.creation).valueOf()
		})
		.splice(0, 10)
}

onMounted(() => {
	// Every list_update reloads the employee's own list too: the server pushes
	// hrms:refetch_resource for `my_*` only while the socket is alive, and a
	// list_update is the one event the room replays after a rejoin.
	for (const [doctype, lists] of Object.entries(REQUEST_LISTS)) {
		useListUpdate(socket, doctype, () => reloadLists([lists.my, ...lists.team], doctype))
	}
	useReloadOnGap(reloadRequestLists)
	reloadRequestLists("mount")
})
</script>
