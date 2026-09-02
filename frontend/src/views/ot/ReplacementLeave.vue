<template>
	<BaseLayout :pageTitle="__('Replacement Leave')">
		<template #body>
			<div class="flex flex-col gap-5 p-4 pt-6">
				<!-- The header, back control and title now come from the shared shell
				     like every other screen (§12, v1.11). This screen had NO header
				     element at all — it was the one view built outside the shell, which
				     is why it also had a hand-rolled back control and a duplicate
				     "New Claim" in its empty state. -->
				<div class="flex items-center justify-end">
					<router-link :to="{ name: 'ReplacementLeaveClaimFormView' }" v-slot="{ navigate }">
						<GButton
							:label="__('New Claim')"
							class="g-btn--compact"
							:disabled="!canClaim"
							@click="navigate"
						/>
					</router-link>
				</div>

				<ResourceError :resource="bank" what="your replacement leave bank" />
				<!-- month bank -->
				<div class="border border-divider rounded-panel p-4 flex flex-col gap-2" v-if="bank.data">
					<span class="g-eyebrow">{{ __("Overtime bank") }}</span>
					<div class="flex items-baseline gap-1.5">
						<span class="text-3xl font-extrabold text-inkbase">
							{{ bank.data.hours_available }}
						</span>
						<span class="text-sm text-ink-600">{{ __("h available") }}</span>
						<span class="text-xs text-ink-600 ml-auto">
							{{ bank.data.hours_claimed }} {{ __("h already claimed") }}
						</span>
					</div>
					<span class="text-xs text-ink-600">
						{{
							__(
								"0.5 day costs 4 h, 1 day costs 8 h. Overtime stays claimable for two payroll cycles (the 16th-to-15th backdate window), then expires; approved days join your Replacement Leave balance until the leave period ends."
							)
						}}
					</span>
				</div>

				<!-- approved OT feeding the bank -->
				<div v-if="bank.data?.requests?.length" class="flex flex-col gap-1.5">
					<span class="g-eyebrow">{{ __("Approved OT — claimable now") }}</span>
					<div
						v-for="request in bank.data.requests"
						:key="request.name"
						class="flex justify-between border-b border-divider py-2 text-sm"
					>
						<span class="text-ink-700">{{ request.ot_date }}</span>
						<span class="font-bold text-inkbase">+{{ request.claimed_hours }} h</span>
					</div>
				</div>

				<!-- claims -->
				<div class="flex flex-col gap-1.5">
					<span class="g-eyebrow">{{ __("My Claims") }}</span>
					<ResourceError v-if="claims.error" :resource="claims" :what="__('your claims')" />
					<GEmptyState
						v-else-if="!claims.data?.length"
						:title="__('No replacement leave claimed')"
						:body="
							canClaim
								? __('Worked a rest day? Use New Claim above to claim the time back')
								: __('No banked overtime to claim this month.')
						"
					/>
					<router-link
						v-for="claimRow in claims.data"
						:key="claimRow.name"
						:to="{ name: 'ReplacementLeaveClaimDetailView', params: { id: claimRow.name } }"
						class="flex justify-between items-center border border-divider rounded-panel p-3 text-sm"
					>
						<div class="flex flex-col">
							<span class="font-bold text-inkbase">
								{{ claimRow.claimed_days }} {{ __("day(s)") }} · −{{ claimRow.hours_cost }} h
							</span>
							<span class="text-xs text-ink-600">{{ claimRow.name }}</span>
						</div>
						<GStatusChip
							:status="claimRow.docstatus === 1 ? 'Approved' : 'Draft'"
							:label="claimRow.docstatus === 1 ? __('Approved') : __('Draft')"
						>
							{{ claimRow.docstatus === 1 ? __("Approved") : __("Pending") }}
						</GStatusChip>
					</router-link>
				</div>
			</div>
		</template>
	</BaseLayout>
</template>

<script setup>
import GStatusChip from "@/components/glass/GStatusChip.vue"
import GEmptyState from "@/components/glass/GEmptyState.vue"
import GButton from "@/components/glass/GButton.vue"
import BaseLayout from "@/components/BaseLayout.vue"
import { createResource } from "frappe-ui"
import { computed, inject } from "vue"

const employee = inject("$employee")
const __ = inject("$translate")

const bank = createResource({
	url: "hrms.api.get_replacement_leave_bank_summary",
	params: { employee: employee.data.name },
	auto: true,
})

const claims = createResource({
	url: "hrms.api.get_replacement_leave_claims",
	params: { employee: employee.data.name, limit: 20 },
	auto: true,
})

// Nothing to convert -> no claim to make. Gate "New Claim" so the user is not
// sent into a form that can only fail (the bank card below explains the 0).
const canClaim = computed(() => (bank.data?.hours_available ?? 0) > 0)
</script>
