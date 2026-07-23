<template>
	<BaseLayout :pageTitle="__('Expense Claims')">
		<template #body>
			<div class="flex flex-col gap-8 px-4 pt-6 pb-8">
				<ExpenseClaimSummary />

				<!-- Claim an expense -->
				<router-link
					:to="{ name: 'ExpenseClaimFormView' }"
					v-slot="{ navigate }"
				>
					<button class="m-btn-primary" @click="navigate">
						{{ __("Claim an Expense") }}
						<svg
							width="17"
							height="17"
							viewBox="0 0 24 24"
							fill="none"
							stroke="currentColor"
							stroke-width="2"
							stroke-linecap="round"
							stroke-linejoin="round"
							class="ml-auto"
						>
							<line x1="5" y1="12" x2="19" y2="12"></line>
							<polyline points="12 5 19 12 12 19"></polyline>
						</svg>
					</button>
				</router-link>

				<!-- Recent expenses -->
				<div>
					<div class="flex items-baseline justify-between mb-2.5">
						<span class="m-kicker !text-ink-600 text-[11px]">
							{{ __("Recent Expenses") }}
						</span>
						<router-link
							:to="{ name: 'ExpenseClaimListView' }"
							class="text-[11px] text-accent-700 underline underline-offset-[3px] cursor-pointer"
						>
							{{ __("View List") }}
						</router-link>
					</div>
					<hr class="m-rule" />
					<RequestList
						:component="markRaw(ExpenseClaimItem)"
						:items="myClaims.data"
					/>
				</div>

				<!-- Advance balance -->
				<div>
					<div class="flex items-baseline justify-between mb-2.5">
						<span class="m-kicker !text-ink-600 text-[11px]">
							{{ __("Advance Balance") }}
						</span>
						<router-link
							:to="{ name: 'EmployeeAdvanceListView' }"
							class="text-[11px] text-accent-700 underline underline-offset-[3px] cursor-pointer"
						>
							{{ __("View List") }}
						</router-link>
					</div>
					<hr class="m-rule" />
					<EmployeeAdvanceBalance :items="advanceBalance.data" />
				</div>
			</div>
		</template>
	</BaseLayout>
</template>

<script setup>
import { markRaw } from "vue"

import BaseLayout from "@/components/BaseLayout.vue"
import ExpenseClaimSummary from "@/components/ExpenseClaimSummary.vue"
import RequestList from "@/components/RequestList.vue"
import ExpenseClaimItem from "@/components/ExpenseClaimItem.vue"
import EmployeeAdvanceBalance from "@/components/EmployeeAdvanceBalance.vue"

import { myClaims } from "@/data/claims"
import { advanceBalance } from "@/data/advances"
</script>
