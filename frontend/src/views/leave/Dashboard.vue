<template>
	<BaseLayout :pageTitle="__('Leaves & Holidays')">
		<template #body>
			<!-- §20.3: one 720px column, left-aligned (7.3 ruling). Was
			     lg:grid-cols-[1fr_280px] over the balance band and lg:grid-cols-2 over
			     the lists, which stranded the primary action in an empty right column
			     and produced three different content widths on one screen. -->
			<div class="flex flex-col gap-8 px-4 pt-6 pb-8 w-full max-w-content-column-lg lg:p-7 lg:gap-10">
				<!-- Top band: balance stat cells + primary action -->
				<div class="flex flex-col gap-8">
					<div class="flex flex-col gap-8">
						<LeaveBalance />
						<ReplacementLeaveCard />
					</div>

					<router-link
						:to="{ name: 'LeaveApplicationFormView' }"
						v-slot="{ navigate }"
						class="block"
					>
						<GButton :label="__('Request a Leave')" @click="navigate">
							<template #trailing>
								<svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
									<line x1="5" y1="12" x2="19" y2="12"></line>
									<polyline points="12 5 19 12 12 19"></polyline>
								</svg>
							</template>
						</GButton>
					</router-link>
				</div>

				<!-- Bottom: recent leaves | upcoming holidays -->
				<div class="flex flex-col gap-8">
					<div>
						<div class="flex flex-row items-baseline justify-between mb-2.5">
							<span class="text-eyebrow uppercase text-accent-ink">{{ __("Recent Leaves") }}</span>
							<router-link
								:to="{ name: 'LeaveApplicationListView' }"
								v-slot="{ navigate }"
							>
								<span
									@click="navigate"
									class="g-seclink text-kra-label text-accent underline underline-offset-link cursor-pointer"
								>
									{{ __("View List") }}
								</span>
							</router-link>
						</div>
						<div class="border-t-2 border-divider">
							<RequestList
								:component="markRaw(LeaveRequestItem)"
								:items="myLeaves.data"
								:emptyStateMessage="__('No leave taken this year. Your applications will appear here once submitted.')"
							/>
						</div>
					</div>

					<div>
						<Holidays />
					</div>
				</div>
			</div>
		</template>
	</BaseLayout>
</template>

<script setup>
import GButton from "@/components/glass/GButton.vue"
import { markRaw } from "vue"

import BaseLayout from "@/components/BaseLayout.vue"
import LeaveBalance from "@/components/LeaveBalance.vue"
import ReplacementLeaveCard from "@/components/ReplacementLeaveCard.vue"
import RequestList from "@/components/RequestList.vue"
import LeaveRequestItem from "@/components/LeaveRequestItem.vue"
import Holidays from "@/components/Holidays.vue"

import { myLeaves } from "@/data/leaves"
</script>
