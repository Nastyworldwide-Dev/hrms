<template>
	<BaseLayout :pageTitle="__('Expense claims')">
		<template #body>
			<div
				class="flex flex-col gap-8 px-4 pt-6 pb-8 w-full max-w-content-column-lg mx-auto lg:py-7"
			>
				<!-- Left: summary poster -->
				<div class="contents">
					<div class="order-1">
						<ExpenseClaimSummary />
					</div>
				</div>

				<!-- Right: recent expenses + claim an expense -->
				<div class="contents">
					<!-- An iOS section: header with its See all, then the group
					     (alpha.9 D19). -->
					<section class="order-3 g-form-section">
						<div class="g-exp-head">
							<h2 class="g-form-section__title">{{ __("Recent expenses") }}</h2>
							<router-link
								:to="{ name: 'ExpenseClaimListView' }"
								class="g-focusable g-seclink text-kra-label text-accent-ink"
							>
								{{ __("See all") }}
							</router-link>
						</div>
						<RequestList
							:component="markRaw(ExpenseClaimItem)"
							:items="myClaims.data"
							:resource="myClaims"
							:what="__('your expense claims')"
						/>
					</section>

					<!-- Claim an expense -->
					<router-link
						:to="{ name: 'ExpenseClaimFormView' }"
						v-slot="{ navigate }"
						class="order-2"
					>
						<GButton :label="__('Claim an expense')" @click="navigate">
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
