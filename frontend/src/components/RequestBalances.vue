<!--
  The standing numbers, where a request is STARTED (revamp §5).

  Nielsen's sixth heuristic — recognition over recall. A person must not have
  to hold a number in their head between two screens, and today they do: the
  leave balance lives on the leave dashboard, and the decision to take leave
  is made on the form. The employees who do not bother checking are the ones
  who file something that gets rejected.

  FOUR THINGS, and each is a DOOR. Tapping "2 days unmarked" opens the list
  already filtered — a number you cannot act on is a number that makes the
  reader do the work of finding what it refers to.

  Leave uses GBalanceGrid/GBalanceCard, which already exist and already handle
  the pro-rated denominator: a mid-year joiner with 7 of 14 has used none of
  it, and a bar reading 7 of 7 would say the opposite.

  A SECTION THE SERVER COULD NOT READ IS ABSENT, not zero. A zero is an
  answer, and the wrong one — "you have no overtime to claim" when the truth
  is "we could not check" sends somebody away from money they are owed.
-->
<template>
	<!-- A FAILED READ IS NOT "YOU HAVE NOTHING". Both rendered nothing, so an
	     employee with 12 days of leave and a broken endpoint saw the same
	     screen as one with none — and this strip exists precisely so nobody has
	     to guess at those numbers. -->
	<GBanner v-if="requestsSummary.error" variant="error">
		{{ __("Your balances could not be loaded. Pull down to try again.") }}
	</GBanner>
	<!-- First load: hold the strip's place (audit F-12: Requests jumped 0.39
	     when it appeared and pushed everything below it down). -->
	<div v-else-if="firstLoad" class="flex flex-col gap-4">
		<!-- The skeleton is hidden from screen readers; this line says what it
		     means (review of 111402a6d). -->
		<span class="sr-only" role="status">{{ __("Loading your balances") }}</span>
		<div class="flex flex-col gap-4" aria-hidden="true">
			<GBalanceGrid loading :cells="4" />
			<GListPanel loading :rows="2" />
		</div>
	</div>
	<div v-else-if="hasAnything" class="flex flex-col gap-4">
		<GBalanceGrid
			v-if="shownLeave.length"
			:count="shownLeave.length"
			:loading="loading && !shownLeave.length"
		>
			<GBalanceCard
				v-for="row in shownLeave"
				:key="row.leave_type"
				:label="row.leave_type"
				:remaining="row.balance"
				:allocated="row.total"
				:entitlement="row.total"
			>
				<!-- "12.5 of 16", not a bare "60". The plan asks for the
				     DENOMINATOR because a number with no scale is not a balance:
				     60 hospitalization days reads as alarming until you know it
				     is 60 of 60, untouched. An expiry replaces it when there is
				     one, because a date is the more urgent of the two. -->
				<template #note>
					<template v-if="row.expiring_soon">{{
						__("Expires {0}", [formatDate(row.expires_on)])
					}}</template>
					<template v-else>{{ __("of {0}", [trim(row.total)]) }}</template>
				</template>
			</GBalanceCard>
		</GBalanceGrid>

		<!-- The types nobody is looking at, behind one tap. Seven cards, two of
		     them wrapping to three lines, is the wall the owner photographed on
		     23 September; four is a strip. What is hidden is the untouched
		     statutory entitlement — not news until it is used. -->
		<button
			v-if="hiddenLeave.length"
			type="button"
			class="g-focusable g-list-more w-full py-3 text-sm text-ink-600 bg-transparent border-none"
			@click="showAllLeave = !showAllLeave"
		>
			{{
				showAllLeave
					? __("Show fewer leave types")
					: __("Show {0} more leave type(s)", [hiddenLeave.length])
			}}
		</button>

		<GListPanel v-if="rows.length">
			<GListRow
				v-for="row in rows"
				:key="row.key"
				:label="row.label"
				:sublabel="row.sublabel"
				@click="row.go()"
			>
				<template #icon>
					<component :is="row.icon" class="g-row-icon" />
				</template>
			</GListRow>
		</GListPanel>
	</div>
</template>

<script setup>
import { computed, inject, onMounted, ref } from "vue"
import { useRouter } from "vue-router"
import { CircleDollarSign, Receipt, UserCheck } from "lucide-vue-next"

import GBalanceCard from "@/components/glass/GBalanceCard.vue"
import GBanner from "@/components/glass/GBanner.vue"
import GBalanceGrid from "@/components/glass/GBalanceGrid.vue"
import GListPanel from "@/components/glass/GListPanel.vue"
import GListRow from "@/components/glass/GListRow.vue"

import { requestsSummary } from "@/data/requestsSummary"

const __ = inject("$translate")
const $dayjs = inject("$dayjs")
const router = useRouter()

const loading = computed(() => Boolean(requestsSummary.loading))
const firstLoad = computed(() => requestsSummary.loading && !requestsSummary.data)
const data = computed(() => requestsSummary.data || {})
const leave = computed(() => data.value.leave || [])
//: Four cards fit a phone without wrapping; seven do not. Measured against
//: the deployed screenshot, where "Compassionate Leave (Immediate Family)"
//: took three lines and pushed everything actionable below the fold.
const LEAVE_SHOWN = 4

const showAllLeave = ref(false)

//: USED FIRST, then the rest. A type the employee has actually drawn on is
//: the one they are checking; an untouched statutory entitlement is a fact
//: they can look up. Expiring types jump the queue either way, because those
//: are the only ones with a deadline attached.
const rankedLeave = computed(() =>
	[...leave.value].sort((a, b) => {
		if (a.expiring_soon !== b.expiring_soon) return a.expiring_soon ? -1 : 1
		const usedA = a.total - a.balance
		const usedB = b.total - b.balance
		if (usedA > 0 !== usedB > 0) return usedA > 0 ? -1 : 1
		return b.balance - a.balance
	})
)

const shownLeave = computed(() =>
	showAllLeave.value ? rankedLeave.value : rankedLeave.value.slice(0, LEAVE_SHOWN)
)
const hiddenLeave = computed(() => rankedLeave.value.slice(LEAVE_SHOWN))

//: A whole number reads as a count; 12.5 days is a real half-day balance.
//: Trailing ".0" on every card is noise.
function trim(value) {
	const n = Number(value)
	return Number.isInteger(n) ? String(n) : n.toFixed(1)
}

function formatDate(value) {
	return value ? $dayjs(value).format("D MMM") : ""
}

function money(amount, currency) {
	// The currency comes from the claims themselves. Without one the number is
	// still the useful part — an employee knows what they spend in.
	return currency ? `${currency} ${Number(amount).toFixed(2)}` : Number(amount).toFixed(2)
}

//: Everything that is not a leave balance: three counters, each a door into
//: the list it counts. Only rows with something to say are built — a strip of
//: permanent zeros is a strip nobody reads.
const rows = computed(() => {
	const out = []
	const overtime = data.value.overtime
	const expenses = data.value.expenses
	const attendance = data.value.attendance

	if (overtime?.unclaimed_days > 0) {
		out.push({
			key: "ot-unclaimed",
			icon: Receipt,
			label: __("{0} day(s) of overtime to claim", [overtime.unclaimed_days]),
			// The hours are what decides whether it is worth doing now.
			sublabel: overtime.unclaimed_hours
				? __("{0} hours", [Number(overtime.unclaimed_hours).toFixed(2)])
				: null,
			go: () => router.push({ name: "OTRequestFormView" }),
		})
	}

	if (expenses?.approved_unpaid_amount > 0) {
		out.push({
			key: "expense-unpaid",
			icon: CircleDollarSign,
			// APPROVED AND UNPAID is the one an employee chases. "Awaiting a
			// decision" is on the request list beside each row; money that was
			// agreed and has not arrived is not visible anywhere else.
			label: __("{0} approved, not yet paid", [
				money(expenses.approved_unpaid_amount, expenses.currency),
			]),
			sublabel: null,
			go: () => router.push({ name: "ExpenseClaimListView" }),
		})
	}

	if (attendance?.days > 0) {
		out.push({
			key: "unmarked",
			icon: UserCheck,
			// The single most common cause of a wrong payslip, and invisible
			// until payroll — by which time the window to fix it has usually
			// closed.
			label: __("{0} day(s) with no attendance", [attendance.days]),
			sublabel: __("Fix these before payroll"),
			go: () => router.push({ name: "AttendanceRequestFormView" }),
		})
	}

	return out
})

const hasAnything = computed(() => leave.value.length > 0 || rows.value.length > 0)

onMounted(() => {
	requestsSummary.fetch()
})
</script>
