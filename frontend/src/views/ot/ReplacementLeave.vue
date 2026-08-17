<template>
	<ion-page>
		<ion-content :fullscreen="true">
			<div class="flex flex-col gap-5 p-4 pt-6">
				<div class="flex items-center justify-between">
					<h1 class="text-xl font-bold text-inkbase">{{ __("Replacement Leave") }}</h1>
					<router-link
						:to="{ name: 'ReplacementLeaveClaimFormView' }"
						v-slot="{ navigate }"
					>
						<Button variant="solid" @click="navigate">
							{{ __("New Claim") }}
						</Button>
					</router-link>
				</div>

				<ResourceError :resource="bank" what="your replacement leave bank" />
				<!-- month bank -->
				<div class="border border-divider p-4 flex flex-col gap-2" v-if="bank.data">
					<span class="m-kicker">{{ monthLabel }} {{ __("bank") }}</span>
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
					<span class="m-kicker">{{ __("Approved OT this month") }}</span>
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
					<span class="m-kicker">{{ __("My Claims") }}</span>
					<EmptyState v-if="!claims.data?.length" :message="__('No claims yet')" />
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
						<Badge :theme="claimRow.docstatus === 1 ? 'green' : 'orange'" variant="subtle">
							{{ claimRow.docstatus === 1 ? __("Approved") : __("Pending") }}
						</Badge>
					</router-link>
				</div>
			</div>
		</ion-content>
	</ion-page>
</template>

<script setup>
import { IonPage, IonContent } from "@ionic/vue"
import { Badge, Button, createResource } from "frappe-ui"
import { computed, inject } from "vue"

import EmptyState from "@/components/EmptyState.vue"

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
</script>
