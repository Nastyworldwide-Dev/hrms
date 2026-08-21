<template>
	<GPage>
		<ion-content :fullscreen="true">
			<div class="flex flex-col gap-5 p-4 pt-6">
				<div class="flex items-center justify-between">
					<!-- This screen is reached from Attendance's action list and is
					     routed OUTSIDE ion-tabs, so it carries no tab bar. Without a
					     back control there was no way off it at all except the
					     device gesture. -->
					<div class="flex items-center gap-1 min-w-0">
						<button
							type="button"
							class="flex items-center justify-center shrink-0"
							:aria-label="__('Back')"
							@click="router.back()"
						>
							<FeatherIcon name="chevron-left" class="h-5 w-5 text-inkbase" />
						</button>
						<h1 class="text-xl font-bold text-inkbase truncate">{{ __("Replacement Leave") }}</h1>
					</div>
					<router-link
						:to="{ name: 'ReplacementLeaveClaimFormView' }"
						v-slot="{ navigate }"
					>
						<GButton :label="__('New Claim')" @click="navigate" />
					</router-link>
				</div>

				<ResourceError :resource="bank" what="your replacement leave bank" />
				<!-- month bank -->
				<div class="border border-divider p-4 flex flex-col gap-2" v-if="bank.data">
					<span class="text-eyebrow uppercase text-accent-ink">{{ monthLabel }} {{ __("bank") }}</span>
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
								"0.5 day costs 4 h, 1 day costs 8 h. Hours not claimed by month end expire; approved days join your Replacement Leave balance until the leave period ends."
							)
						}}
					</span>
				</div>

				<!-- approved OT feeding the bank -->
				<div v-if="bank.data?.requests?.length" class="flex flex-col gap-1.5">
					<span class="text-eyebrow uppercase text-accent-ink">{{ __("Approved OT this month") }}</span>
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
					<span class="text-eyebrow uppercase text-accent-ink">{{ __("My Claims") }}</span>
					<GEmptyState
						v-if="!claims.data?.length"
						:title="__('No replacement leave claimed')"
						:body="__('Worked a rest day? Claim the time back here')"
					/>
					<router-link
						v-for="claimRow in claims.data"
						:key="claimRow.name"
						:to="{ name: 'ReplacementLeaveClaimDetailView', params: { id: claimRow.name } }"
						class="flex justify-between items-center border border-divider p-3 text-sm"
					>
						<div class="flex flex-col">
							<span class="font-bold text-inkbase">
								{{ claimRow.claimed_days }} {{ __("day(s)") }} · −{{ claimRow.hours_cost }} h
							</span>
							<span class="text-xs text-ink-600">{{ claimRow.name }}</span>
						</div>
						<GStatusChip :status="claimRow.docstatus === 1 ? 'Approved' : 'Draft'" :label="claimRow.docstatus === 1 ? __('Approved') : __('Draft')">
							{{ claimRow.docstatus === 1 ? __("Approved") : __("Pending") }}
						</GStatusChip>
					</router-link>
				</div>
			</div>
		</ion-content>
	</GPage>
</template>

<script setup>
import { useRouter } from "vue-router"
import GStatusChip from "@/components/glass/GStatusChip.vue"
import GEmptyState from "@/components/glass/GEmptyState.vue"
import GButton from "@/components/glass/GButton.vue"
import GPage from "@/components/glass/GPage.vue"
import { IonContent } from "@ionic/vue"
import { Badge, Button, FeatherIcon, createResource } from "frappe-ui"
import { computed, inject } from "vue"


const employee = inject("$employee")
const __ = inject("$translate")
const dayjs = inject("$dayjs")

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

const monthLabel = computed(() =>
	bank.data?.month_start ? dayjs(bank.data.month_start).format("MMMM YYYY") : ""
)

const router = useRouter()
</script>
