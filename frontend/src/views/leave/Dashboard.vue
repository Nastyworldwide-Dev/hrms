<template>
	<BaseLayout :pageTitle="__('Leave and holidays')">
		<template #body>
			<!-- §20.3: one 720px column, left-aligned (7.3 ruling). Was
			     lg:grid-cols-[1fr_280px] over the balance band and lg:grid-cols-2 over
			     the lists, which stranded the primary action in an empty right column
			     and produced three different content widths on one screen. -->
			<div
				class="flex flex-col gap-8 px-4 pt-6 pb-8 w-full max-w-content-column-lg mx-auto lg:p-7 lg:gap-10"
			>
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
						<GButton :label="__('Ask for time off')" @click="navigate">
							<template #trailing>
								<ArrowRight :size="17" />
							</template>
						</GButton>
					</router-link>
				</div>

				<!-- Bottom: recent leaves | upcoming holidays -->
				<div class="flex flex-col gap-8">
					<div>
						<div class="flex flex-row items-baseline justify-between mb-2.5">
							<span class="g-eyebrow">{{ __("Recent leave") }}</span>
							<router-link
								:to="{ name: 'LeaveApplicationListView' }"
								class="g-focusable g-seclink text-kra-label text-accent-ink underline underline-offset-link"
							>
								{{ __("View list") }}
							</router-link>
						</div>
						<div class="border-t-2 border-divider">
							<RequestList
								:component="markRaw(LeaveRequestItem)"
								:items="myLeaves.data"
								:resource="myLeaves"
								:what="__('your leave')"
								:emptyStateMessage="
									__(
										'No leave taken this year. Your applications will appear here once submitted.'
									)
								"
							/>
						</div>
					</div>
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
import LeaveBalance from "@/components/LeaveBalance.vue"
import ReplacementLeaveCard from "@/components/ReplacementLeaveCard.vue"
import RequestList from "@/components/RequestList.vue"
import LeaveRequestItem from "@/components/LeaveRequestItem.vue"

import { myLeaves } from "@/data/leaves"
</script>
