<template>
	<BaseLayout :pageTitle="__('Leaves & Holidays')">
		<template #body>
			<div class="flex flex-col gap-8 px-4 pt-6 pb-8 w-full lg:p-7 lg:gap-10">
				<!-- Top band: balance stat cells + primary action -->
				<div
					class="contents lg:grid lg:grid-cols-[1fr_280px] lg:gap-x-0 lg:items-stretch"
				>
					<div class="lg:pr-8 flex flex-col gap-8">
						<LeaveBalance />
						<ReplacementLeaveCard />
					</div>

					<router-link
						:to="{ name: 'LeaveApplicationFormView' }"
						v-slot="{ navigate }"
						class="lg:border-l lg:border-divider lg:pl-8 lg:flex lg:items-center"
					>
						<button @click="navigate" class="m-btn-primary">
							{{ __("Request a Leave") }}
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

				<!-- Bottom: recent leaves | upcoming holidays -->
				<div class="contents lg:grid lg:grid-cols-2 lg:gap-x-0 lg:items-start">
					<div class="lg:pr-8">
						<div class="flex flex-row items-baseline justify-between mb-2.5">
							<span class="m-kicker">{{ __("Recent Leaves") }}</span>
							<router-link
								:to="{ name: 'LeaveApplicationListView' }"
								v-slot="{ navigate }"
							>
								<span
									@click="navigate"
									class="text-[11px] text-accent underline underline-offset-[3px] cursor-pointer"
								>
									{{ __("View List") }}
								</span>
							</router-link>
						</div>
						<div class="border-t-2 border-divider">
							<RequestList
								:component="markRaw(LeaveRequestItem)"
								:items="myLeaves.data"
							/>
						</div>
					</div>

					<div class="lg:border-l lg:border-divider lg:pl-8">
						<Holidays />
					</div>
				</div>
			</div>
		</template>
	</BaseLayout>
</template>

<script setup>
import { markRaw } from "vue"

import BaseLayout from "@/components/BaseLayout.vue"
import LeaveBalance from "@/components/LeaveBalance.vue"
import ReplacementLeaveCard from "@/components/ReplacementLeaveCard.vue"
import RequestList from "@/components/RequestList.vue"
import LeaveRequestItem from "@/components/LeaveRequestItem.vue"
import Holidays from "@/components/Holidays.vue"

import { myLeaves } from "@/data/leaves"
</script>
