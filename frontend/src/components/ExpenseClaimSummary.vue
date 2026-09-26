<template>
	<div class="flex flex-col gap-stack-md w-full" v-if="summary.data">
		<!-- A plain group with the big figure (alpha.9 D20): lime is kept for
		     the screen's one action, "Claim an expense". -->
		<div class="g-poster">
			<div class="g-eyebrow-type g-poster__label">
				{{ __("Total claimed") }}
			</div>
			<div class="g-poster__figure tabular-nums">
				{{ formatCurrency(total_claimed_amount, company_currency) }}
			</div>
		</div>

		<!-- One row per status, amount trailing, as iOS Wallet lists them
		     (alpha.12 A6). Three 110 pt tiles cut "RM 1,250.00" off and said
		     each label twice (measured). The label is the signal, never colour. -->
		<GListPanel>
			<GListRow :label="__('Waiting')" :amount="pendingAmount" :tappable="false" :chevron="false" />
			<GListRow :label="__('Approved')" :amount="approvedAmount" :tappable="false" :chevron="false" />
			<GListRow :label="__('Rejected')" :amount="rejectedAmount" :tappable="false" :chevron="false" />
		</GListPanel>
	</div>
	<!-- Without this the component rendered NOTHING when its request failed:
	     no calendar, no message, nothing to search for. Four features were
	     reported "missing" that were in fact erroring. -->
	<div v-else-if="summary.error" class="text-p-sm text-ink-500 py-6 text-center">
		{{ __("Could not load the expense summary. Refresh to try again.") }}
	</div>
	<!-- Four states (D6): the poster and the stat row as skeletons while the
	     first read is in flight, so the screen does not open on a blank. -->
	<div v-else-if="summary.loading" class="flex flex-col gap-stack-md w-full" aria-hidden="true">
		<GSkeleton height="96px" radius="var(--g-radius-card)" />
		<GSkeleton height="64px" radius="var(--g-radius-panel)" />
	</div>
</template>

<script setup>
import { computed } from "vue"

import { expenseClaimSummary as summary } from "@/data/claims"
import GSkeleton from "@/components/glass/GSkeleton.vue"
import GListPanel from "@/components/glass/GListPanel.vue"
import GListRow from "@/components/glass/GListRow.vue"

import { formatCurrency } from "@/utils/formatters"

const total_claimed_amount = computed(() => {
	return (
		summary.data?.total_pending_amount +
		summary.data?.total_claimed_in_approved +
		summary.data?.total_rejected_amount
	)
})

const company_currency = computed(() => summary.data?.currency)

const pendingAmount = computed(() =>
	formatCurrency(summary.data?.total_pending_amount || 0, company_currency.value)
)
const approvedAmount = computed(() =>
	formatCurrency(summary.data?.total_approved_amount || 0, company_currency.value)
)
//: Rejected outright, plus the part of approved claims that was cut.
const rejectedAmount = computed(() =>
	formatCurrency(
		(summary.data?.total_rejected_amount || 0) +
			((summary.data?.total_claimed_in_approved || 0) - (summary.data?.total_approved_amount || 0)),
		company_currency.value
	)
)
</script>
