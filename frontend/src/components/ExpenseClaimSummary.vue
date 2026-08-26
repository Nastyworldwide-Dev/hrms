<template>
	<div class="flex flex-col gap-stack-md w-full" v-if="summary.data">
		<!-- The screen's one accent surface. See `.g-poster` in the theme layer
		     for why its ink is --g-on-brand rather than `text-ground`, which
		     measured 1.03 in light theme. -->
		<div class="g-poster">
			<div class="g-eyebrow-type g-poster__label">
				{{ __("Total Claimed") }}
			</div>
			<div class="g-poster__figure tabular-nums">
				{{ formatCurrency(total_claimed_amount, company_currency) }}
			</div>
		</div>

		<!-- GStatPanel, not a hand-rolled grid. It is the §15.2 flattened stat
		     row - ONE glass surface with internal hair dividers - and until now
		     it rendered on no production screen at all, only the design
		     specimen, while this screen open-coded the same shape without the
		     panel. Same class of drift as the four avatars in RC18. -->
		<GStatPanel>
			<GStatTile
				:value="formatCurrency(summary.data?.total_pending_amount || 0, company_currency)"
				:label="__('Pending')"
			/>
			<GStatTile
				:value="formatCurrency(summary.data?.total_approved_amount || 0, company_currency)"
				:label="__('Approved')"
			/>
			<!-- Was `text-accent-700`, which resolves to --g-accent-ink and
			     therefore to --g-brand in dark: a REJECTED figure rendered in the
			     brand colour. All three cells are neutral now - the label is the
			     signal, per §14.1's rule that colour is never the only one. -->
			<GStatTile
				:value="
					formatCurrency(
						(summary.data?.total_rejected_amount || 0) +
							((summary.data?.total_claimed_in_approved || 0) -
								(summary.data?.total_approved_amount || 0)),
						company_currency
					)
				"
				:label="__('Rejected')"
			/>
		</GStatPanel>
	</div>
	<!-- Without this the component rendered NOTHING when its request failed:
	     no calendar, no message, nothing to search for. Four features were
	     reported "missing" that were in fact erroring. -->
	<div v-else-if="summary.error" class="text-p-sm text-ink-500 py-6 text-center">
		{{ __("Could not load the expense summary. Refresh to try again.") }}
	</div>
</template>

<script setup>
import { computed } from "vue"

import { expenseClaimSummary as summary } from "@/data/claims"
import GStatPanel from "@/components/glass/GStatPanel.vue"
import GStatTile from "@/components/glass/GStatTile.vue"

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
