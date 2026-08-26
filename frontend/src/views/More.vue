<template>
	<BaseLayout :pageTitle="__('More')">
		<template #body>
			<div
				class="flex flex-col gap-[13px] w-full max-w-content-column-lg px-4 pt-[18px] pb-24 lg:p-7"
			>
				<span class="g-eyebrow">{{ __("More") }}</span>

				<!-- one glass surface for the whole list (§15.1): the panel and its
				     rows count as ONE, not one per row -->
				<GListPanel>
					<GListRow
						v-for="item in moreItems"
						:key="item.route"
						:label="item.title"
						@click="router.push(item.route)"
					>
						<template #icon>
							<component :is="item.icon" class="h-[17px] w-[17px]" />
						</template>
					</GListRow>
				</GListPanel>
			</div>
		</template>
	</BaseLayout>
</template>

<script setup>
import { useRouter } from "vue-router"
import { computed, inject, markRaw } from "vue"

import BaseLayout from "@/components/BaseLayout.vue"
import GListPanel from "@/components/glass/GListPanel.vue"
import GListRow from "@/components/glass/GListRow.vue"
import TeamIcon from "@/components/icons/TeamIcon.vue"
import { MORE_ITEMS } from "@/data/navItems"
import { hasTeam } from "@/data/team"

const router = useRouter()
const __ = inject("$translate")

// Team is manager-only: the entry appears once has_team confirms direct reports
// (or the caller is HR, who browse teams via the selector)
const moreItems = computed(() => {
	const items = MORE_ITEMS.map((item) => ({ ...item, title: __(item.title) }))
	if (hasTeam.data) {
		items.push({ icon: markRaw(TeamIcon), title: __("Team"), route: "/team" })
		// §13.1 lists Remote Approvals behind More; it had no entry in any nav
		// surface before, reachable only by typing the URL
		items.push({
			icon: markRaw(TeamIcon),
			title: __("Remote Approvals"),
			route: "/remote-approvals",
		})
	}
	return items
})
</script>
