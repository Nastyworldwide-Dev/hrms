<template>
	<BaseLayout :pageTitle="__('More')">
		<template #body>
			<div
				class="flex flex-col gap-2 w-full max-w-[720px] px-4 pt-[18px] pb-24 lg:p-7"
			>
				<span class="m-kicker">{{ __("More") }}</span>
				<div class="flex flex-col border-t-2 border-divider">
					<router-link
						v-for="item in moreItems"
						:key="item.route"
						:to="item.route"
						class="flex items-center gap-3 bg-surface border-b border-divider p-3.5 no-underline active:scale-[0.985] active:bg-ink-200"
						style="transition: transform var(--motion-press), background-color var(--motion-press)"
					>
						<component
							:is="item.icon"
							class="h-[19px] w-[19px] flex-none text-accent-700"
						/>
						<span class="flex-1 font-extrabold text-[13px] text-inkbase">
							{{ item.title }}
						</span>
						<FeatherIcon
							name="chevron-right"
							class="h-4 w-4 flex-none text-ink-400"
						/>
					</router-link>
				</div>
			</div>
		</template>
	</BaseLayout>
</template>

<script setup>
import { FeatherIcon } from "frappe-ui"
import { inject } from "vue"

import BaseLayout from "@/components/BaseLayout.vue"
import { MORE_ITEMS } from "@/data/navItems"

const __ = inject("$translate")

const moreItems = MORE_ITEMS.map((item) => ({ ...item, title: __(item.title) }))
</script>
