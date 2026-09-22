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
						<RequestList
							:component="markRaw(ExpenseClaimItem)"
							:items="myClaims.data"
							:resource="myClaims"
							:what="__('your expense claims')"
						/>
					</div>

					<!-- Claim an expense -->
					<router-link
						:to="{ name: 'ExpenseClaimFormView' }"
						v-slot="{ navigate }"
						class="order-2 lg:order-2"
					>
						<GButton :label="__('Claim an Expense')" @click="navigate">
							<template #trailing>
								<ArrowRight :size="17" />
							</template>
						</GButton>
					</router-link>
				</div>
			</div>
		</template>
	</BaseLayout>
</template>

<script setup>
import { ArrowRight } from "lucide-vue-next"
import GButton from "@/components/glass/GButton.vue"
import { markRaw } from "vue"

import BaseLayout from "@/components/BaseLayout.vue"
import ExpenseClaimSummary from "@/components/ExpenseClaimSummary.vue"
import RequestList from "@/components/RequestList.vue"
import ExpenseClaimItem from "@/components/ExpenseClaimItem.vue"

import { myClaims } from "@/data/claims"
</script>
