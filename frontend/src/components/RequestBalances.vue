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
	<div v-if="hasAnything" class="flex flex-col gap-4">
		<GBalanceGrid v-if="leave.length" :count="leave.length" :loading="loading && !leave.length">
			<GBalanceCard
				v-for="row in leave"
				:key="row.leave_type"
				:label="row.leave_type"
				:remaining="row.balance"
				:allocated="row.total"
				:entitlement="row.total"
			>
				<template v-if="row.expiring_soon" #note>
					{{ __("Expires {0}", [formatDate(row.expires_on)]) }}
				</template>
			</GBalanceCard>
		</GBalanceGrid>

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
import { computed, inject, onMounted } from "vue"
import { useRouter } from "vue-router"
import { CircleDollarSign, Receipt, UserCheck } from "lucide-vue-next"

import GBalanceCard from "@/components/glass/GBalanceCard.vue"
import GBalanceGrid from "@/components/glass/GBalanceGrid.vue"
import GListPanel from "@/components/glass/GListPanel.vue"
import GListRow from "@/components/glass/GListRow.vue"

import { requestsSummary } from "@/data/requestsSummary"

const __ = inject("$translate")
const $dayjs = inject("$dayjs")
const router = useRouter()

const loading = computed(() => Boolean(requestsSummary.loading))
const data = computed(() => requestsSummary.data || {})
const leave = computed(() => data.value.leave || [])

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
