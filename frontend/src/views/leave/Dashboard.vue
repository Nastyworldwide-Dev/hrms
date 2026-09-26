<template>
	<BaseLayout :pageTitle="__('Time off')">
		<template #body>
			<!-- §20.3: one 720px column, left-aligned (7.3 ruling). Was
			     lg:grid-cols-[1fr_280px] over the balance band and lg:grid-cols-2 over
			     the lists, which stranded the primary action in an empty right column
			     and produced three different content widths on one screen. -->
			<div
				class="flex flex-col gap-8 px-4 pt-6 pb-8 w-full max-w-content-column-lg mx-auto lg:py-7 lg:gap-10"
			>
				<!-- Top band: balance stat cells + primary action -->
				<div class="flex flex-col gap-8">
					<div class="flex flex-col gap-8">
						<LeaveBalance />
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
					<!-- An iOS section: header with its See all, then the group
					     (alpha.9 D19: a loose header over a hand-ruled table). -->
					<section class="g-form-section">
						<div class="g-exp-head">
							<h2 class="g-form-section__title">{{ __("Recent leave") }}</h2>
							<router-link
								:to="{ name: 'LeaveApplicationListView' }"
								class="g-focusable g-seclink text-kra-label text-accent-ink"
							>
								{{ __("See all") }}
							</router-link>
						</div>
						<div>
							<RequestList
								:component="markRaw(LeaveRequestItem)"
								:items="myLeaves.data"
								:resource="myLeaves"
								:what="__('your leave')"
								:emptyStateMessage="
									__(
										'No time off taken this year. Time off you ask for shows up here.'
									)
								"
							/>
						</div>
					</section>
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
import RequestList from "@/components/RequestList.vue"
import LeaveRequestItem from "@/components/LeaveRequestItem.vue"

import { myLeaves } from "@/data/leaves"
</script>
