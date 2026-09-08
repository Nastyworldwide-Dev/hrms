<template>
	<BaseLayout :pageTitle="__('More')">
		<template #body>
			<div
				class="flex flex-col gap-[13px] w-full max-w-content-column-lg mx-auto px-4 pt-[18px] pb-24 lg:p-7"
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

				<!-- Sibling apps on the same site. A row here LEAVES the PWA (full
				     navigation, not a router push — each app owns its own scope), so
				     it trails an arrow-out glyph instead of the chevron. Second glass
				     surface on this screen, well inside the §15 budget. -->
				<span class="g-eyebrow mt-[5px]">{{ __("Apps") }}</span>
				<GListPanel>
					<GListRow
						v-for="item in appItems"
						:key="item.key"
						:label="item.title"
						:sublabel="item.sublabel"
						:chevron="false"
						@click="openApp(item)"
					>
						<template #icon>
							<component :is="item.icon" class="h-[17px] w-[17px]" />
						</template>
						<template #badge>
							<ExternalLinkIcon class="flex-none text-ink-3" aria-hidden="true" />
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
import ExternalLinkIcon from "@/components/icons/ExternalLinkIcon.vue"
import { MORE_ITEMS, APP_ITEMS, HELPDESK_ITEM } from "@/data/navItems"
import { isSameOriginPath } from "@/data/appLinks"
import { hasTeam } from "@/data/team"
import { helpdeskAvailable } from "@/data/helpdesk"

const router = useRouter()
const __ = inject("$translate")

// Team is manager-only: the entry appears once has_team confirms direct reports
// (or the caller is HR, who browse teams via the selector)
const moreItems = computed(() => {
	const items = MORE_ITEMS.map((item) => ({ ...item, title: __(item.title) }))
	// native Helpdesk, only where the app is installed on this site
	if (helpdeskAvailable.data) items.push({ ...HELPDESK_ITEM, title: __(HELPDESK_ITEM.title) })
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

const appItems = computed(() =>
	APP_ITEMS.map((item) => ({ ...item, title: __(item.title), sublabel: __(item.sublabel) }))
)

// Full navigation on purpose: the target SPA is outside vue-router's /hrms
// base. Same origin, so the session cookie carries over. From an installed
// PWA this opens in the OS in-app browser (out of scope) — accepted.
const openApp = (item) => {
	if (!isSameOriginPath(item.href)) {
		console.warn("[More] refusing non-local app link:", item.href)
		return
	}
	console.info("[More] leaving PWA for sibling app:", item.key)
	window.location.assign(item.href)
}
</script>
