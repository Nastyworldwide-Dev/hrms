<template>
	<BaseLayout :pageTitle="__('Expense Claims')">
		<template #body>
			<div
				class="flex flex-col gap-8 px-4 pt-6 pb-8 lg:grid lg:grid-cols-[1fr_1.2fr] lg:gap-x-0 lg:p-7 lg:items-start"
			>
				<!-- Left: summary poster, advance balance, request an advance -->
				<div class="contents lg:flex lg:flex-col lg:gap-8 lg:pr-8">
					<div class="order-1">
						<ExpenseClaimSummary />
					</div>

					<!-- Advance balance -->
					<div class="order-4">
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

					<!-- Request an advance -->
					<router-link
						:to="{ name: 'EmployeeAdvanceFormView' }"
						v-slot="{ navigate }"
						class="order-5"
					>
						<button
							type="button"
							class="flex items-center w-full bg-transparent text-inkbase border border-divider px-4 py-3.5 font-bold text-sm text-left hover:bg-ink-200"
							@click="navigate"
						>
							{{ __("Request an Advance") }}
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
				</div>

				<!-- Right: recent expenses + claim an expense -->
				<div
					class="contents lg:flex lg:flex-col lg:gap-8 lg:border-l lg:border-divider lg:pl-8"
				>
					<div class="order-3 lg:order-1">
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

					<!-- Claim an expense -->
					<router-link
						:to="{ name: 'ExpenseClaimFormView' }"
						v-slot="{ navigate }"
						class="order-2 lg:order-2"
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
