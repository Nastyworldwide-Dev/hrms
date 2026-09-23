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

  Leave is ONE line of what is left (owner ruling, 23 Sep 2026: the Requests
  page fits one phone screen). The pro-rated denominator — a mid-year joiner
  with 7 of 14 has used none of it — and any expiry are in the All balances
  sheet, one tap away.

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
			<GListPanel loading :rows="1" />
		</div>
	</div>
	<div v-else-if="hasAnything" class="flex flex-col gap-4">
		<!-- Owner ruling (23 Sep, one-screen Requests): the balances are ONE
		     line, "Annual 6 · Medical 13 · All balances ›" — the two cards took
		     a third of the phone. The numbers are what is LEFT; the "of 14" and
		     any expiry are one tap away, in the All balances sheet. -->
		<div v-if="shownLeave.length" class="flex items-center justify-between gap-3">
			<p class="text-sm text-ink" data-testid="balances-line">{{ line }}</p>
			<button
				type="button"
				class="g-focusable g-list-more px-2 text-sm text-ink-600 bg-transparent border-none"
				@click="openAll"
			>
				{{ __("All balances") }} ›
			</button>
		</div>
		<GModal :is-open="allOpen" :title="__('All balances')" @did-dismiss="allOpen = false">
			<GListPanel>
				<GListRow
					v-for="row in rankedLeave"
					:key="row.leave_type"
					:label="row.leave_type"
					:sublabel="balanceLine(row)"
					:tappable="false"
				/>
			</GListPanel>
		</GModal>

		<!-- Needs attention: one line each, and only what is non-zero. The
		     eyebrow goes with them — a heading over nothing is noise. -->
		<template v-if="rows.length">
			<div class="g-eyebrow">{{ __("Needs attention") }}</div>
			<GListPanel>
				<GListRow
					v-for="row in rows"
					:key="row.key"
					:label="row.label"
					:amount="row.amount"
					@click="row.go()"
				>
					<template #icon>
						<component :is="row.icon" class="g-row-icon" />
					</template>
				</GListRow>
			</GListPanel>
		</template>
	</div>
</template>

<script setup>
import { countOf } from "@/utils/countWords"
import { formatCurrency } from "@/utils/formatters"
import { hoursAsTime } from "@/utils/daySheet"
import { computed, inject, onMounted, ref } from "vue"
import { useRouter } from "vue-router"
import { CircleDollarSign, Receipt, UserCheck } from "lucide-vue-next"

import GBanner from "@/components/glass/GBanner.vue"
import GListPanel from "@/components/glass/GListPanel.vue"
import GListRow from "@/components/glass/GListRow.vue"
import GModal from "@/components/glass/GModal.vue"

import { requestsSummary } from "@/data/requestsSummary"
import { balancesLine, trimNumber as trim } from "@/utils/requestsPage"
import { unmarkedLabel, unmarkedRoute } from "@/utils/unmarkedLabel"

const __ = inject("$translate")
const $dayjs = inject("$dayjs")
const router = useRouter()

const firstLoad = computed(() => requestsSummary.loading && !requestsSummary.data)
const data = computed(() => requestsSummary.data || {})
const leave = computed(() => data.value.leave || [])
//: Two names fit the one balances line on a phone; the rest are in the sheet.
const LEAVE_SHOWN = 2
//: Annual and Medical lead the strip (owner ruling R2), matched by name
//: because every site names its leave types its own way.
//: "Privilege" and "Earned" are ERPNext's usual names for annual leave.
const PINNED = [/annual|privilege|earned/i, /medical|sick/i]
const pin = (row) => {
	const at = PINNED.findIndex((re) => re.test(row.leave_type || ""))
	return at === -1 ? PINNED.length : at
}

const allOpen = ref(false)

//: USED FIRST, then the rest. A type the employee has actually drawn on is
//: the one they are checking; an untouched statutory entitlement is a fact
//: they can look up. Expiring types jump the queue either way, because those
//: are the only ones with a deadline attached.
const rankedLeave = computed(() =>
	[...leave.value].sort((a, b) => {
		if (pin(a) !== pin(b)) return pin(a) - pin(b)
		if (a.expiring_soon !== b.expiring_soon) return a.expiring_soon ? -1 : 1
		const usedA = a.total - a.balance
		const usedB = b.total - b.balance
		if (usedA > 0 !== usedB > 0) return usedA > 0 ? -1 : 1
		return b.balance - a.balance
	})
)

const shownLeave = computed(() => rankedLeave.value.slice(0, LEAVE_SHOWN))
//: "Annual 6 · Medical 13" — the pinned pair, remaining balance, trimmed.
const line = computed(() => balancesLine(shownLeave.value))

function openAll() {
	console.info("[RequestBalances] opening all balances", leave.value.length)
	allOpen.value = true
}

//: "6 of 14 left" — or the expiry, when there is one, as on the cards.
function balanceLine(row) {
	if (row.expiring_soon)
		return __("{0} left · expires {1}", [trim(row.balance), formatDate(row.expires_on)])
	return __("{0} of {1} left", [trim(row.balance), trim(row.total)])
}

function formatDate(value) {
	return value ? $dayjs(value).format("D MMM") : ""
}

function money(amount, currency) {
	// The app's one money formatter: "RM 50", the symbol, not the code (live
	// audit 23 Sep: "INR 50.00" here while every other screen said "RM").
	return currency ? formatCurrency(amount, currency) : Number(amount).toFixed(2)
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
			label: __("{0} of overtime to claim", [countOf(overtime.unclaimed_days, __("day"))]),
			// The hours are what decides whether it is worth doing now; they sit
			// on the right so the row stays one line (one-screen Requests).
			amount: overtime.unclaimed_hours
				? hoursAsTime(overtime.unclaimed_hours)
				: "",
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
			amount: "",
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
			// "before payroll" is why it matters; kept on the one line (design
			// review of ca6a6b9d9: the urgency was dropped with the sublabel).
			// Names the day (owner bug, 23 Sep 2026) and opens it on the
			// Calendar, where the day sheet offers the fix.
			label: unmarkedLabel(attendance, __),
			amount: "",
			go: () => router.push(unmarkedRoute(attendance)),
		})
	}

	return out
})

const hasAnything = computed(() => leave.value.length > 0 || rows.value.length > 0)

onMounted(() => {
	requestsSummary.fetch()
})
</script>
