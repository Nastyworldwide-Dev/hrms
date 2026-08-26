<template>
	<BaseLayout :pageTitle="__('Expense Claims')">
		<template #body>
			<div
				class="flex flex-col gap-8 px-4 pt-6 pb-8 lg:grid lg:grid-cols-[1fr_1.2fr] lg:gap-x-0 lg:p-7 lg:items-start"
			>
				<!-- Left: summary poster -->
				<div class="contents lg:flex lg:flex-col lg:gap-8 lg:pr-8">
					<div class="order-1">
						<ExpenseClaimSummary />
					</div>
				</div>

				<!-- Right: recent expenses + claim an expense -->
				<div class="contents lg:flex lg:flex-col lg:gap-8 lg:border-l lg:border-divider lg:pl-8">
					<div class="order-3 lg:order-1">
						<div class="flex items-baseline justify-between mb-2.5">
							<span class="g-eyebrow !text-ink-600">
								{{ __("Recent Expenses") }}
							</span>
							<router-link
								:to="{ name: 'ExpenseClaimListView' }"
								class="g-seclink text-kra-label text-accent-700 underline underline-offset-link cursor-pointer"
							>
								{{ __("View List") }}
							</router-link>
						</div>
						<hr class="h-px border-0 bg-hair" />
						<RequestList :component="markRaw(ExpenseClaimItem)" :items="myClaims.data" />
					</div>

					<!-- Claim an expense -->
					<router-link
						:to="{ name: 'ExpenseClaimFormView' }"
						v-slot="{ navigate }"
						class="order-2 lg:order-2"
					>
						<GButton :label="__('Claim an Expense')" @click="navigate">
							<template #trailing>
								<svg
									width="17"
									height="17"
									viewBox="0 0 24 24"
									fill="none"
									stroke="currentColor"
									stroke-width="2"
									stroke-linecap="round"
									stroke-linejoin="round"
								>
									<line x1="5" y1="12" x2="19" y2="12"></line>
									<polyline points="12 5 19 12 12 19"></polyline>
								</svg>
							</template>
						</GButton>
					</router-link>
				</div>
			</div>
		</template>
	</BaseLayout>
</template>

<script setup>
import GButton from "@/components/glass/GButton.vue"
import { markRaw } from "vue"

import BaseLayout from "@/components/BaseLayout.vue"
import ExpenseClaimSummary from "@/components/ExpenseClaimSummary.vue"
import RequestList from "@/components/RequestList.vue"
import ExpenseClaimItem from "@/components/ExpenseClaimItem.vue"

import { myClaims } from "@/data/claims"
</script>
