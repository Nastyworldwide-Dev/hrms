<template>
	<div class="flex flex-col w-full" v-if="summary.data">
		<!-- Poster: total claimed -->
		<div class="m-poster px-4 pt-5 pb-[22px]">
			<div class="font-sans font-extrabold text-[10px] tracking-[0.1em] uppercase text-accent-200">
				{{ __("Total Claimed") }}
			</div>
			<div
				class="font-sans font-extrabold text-[38px] leading-[1.05] tabular-nums text-ground mt-1.5"
			>
				{{ formatCurrency(total_claimed_amount, company_currency) }}
			</div>
		</div>

		<!-- Stat cells: pending / approved / rejected -->
		<div class="grid grid-cols-3 border-b-2 border-divider">
			<div class="flex flex-col gap-0.5 py-3 pl-0.5 pr-3">
				<span class="text-[9px] tracking-[0.08em] uppercase text-ink-600">
					{{ __("Pending") }}
				</span>
				<span class="font-sans font-extrabold text-base tabular-nums">
					{{ formatCurrency(summary.data?.total_pending_amount || 0, company_currency) }}
				</span>
			</div>
			<div class="flex flex-col gap-0.5 py-3 px-3 border-l border-divider">
				<span class="text-[9px] tracking-[0.08em] uppercase text-ink-600">
					{{ __("Approved") }}
				</span>
				<span class="font-sans font-extrabold text-base tabular-nums">
					{{ formatCurrency(summary.data?.total_approved_amount || 0, company_currency) }}
				</span>
			</div>
			<div class="flex flex-col gap-0.5 py-3 pl-3 pr-0.5 border-l border-divider">
				<span class="text-[9px] tracking-[0.08em] uppercase text-accent-700">
					{{ __("Rejected") }}
				</span>
				<span class="font-sans font-extrabold text-base tabular-nums text-accent-700">
					{{
						formatCurrency(
							(summary.data?.total_rejected_amount || 0) +
								((summary.data?.total_claimed_in_approved || 0) -
									(summary.data?.total_approved_amount || 0)),
							company_currency
						)
					}}
				</span>
			</div>
		</div>
	</div>
</template>

<script setup>
import { computed } from "vue"

import { expenseClaimSummary as summary } from "@/data/claims"

import { formatCurrency } from "@/utils/formatters"

const total_claimed_amount = computed(() => {
	return (
		summary.data?.total_pending_amount +
		summary.data?.total_claimed_in_approved +
		summary.data?.total_rejected_amount
	)
})

const company_currency = computed(() => summary.data?.currency)
</script>
