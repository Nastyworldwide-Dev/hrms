<template>
	<BaseLayout :pageTitle="__('More')">
		<template #body>
			<div
				class="flex flex-col gap-3 w-full max-w-content-column-lg mx-auto px-4 pt-4 pb-24 lg:p-7"
			>
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
							<component :is="item.icon" class="h-icon-md w-icon-md" />
						</template>
					</GListRow>
					<!-- One list of the year ahead, in a sheet (PAGE-20): its only
					     door was inside the Leaves dashboard, which More no longer
					     lists. -->
					<GListRow :label="__('Public holidays')" @click="holidaysOpen = true">
						<template #icon>
							<CalendarDays class="h-icon-md w-icon-md" />
						</template>
					</GListRow>
				</GListPanel>

				<GModal :is-open="holidaysOpen" @did-dismiss="holidaysOpen = false">
					<HolidayList v-if="holidaysOpen && employee.data" />
				</GModal>

				<!-- Sibling apps on the same site. A row here LEAVES the PWA (full
				     navigation, not a router push — each app owns its own scope), so
				     it trails an arrow-out glyph instead of the chevron. Second glass
				     surface on this screen, well inside the §15 budget. -->
				<template v-if="appItems.length">
					<span class="g-eyebrow mt-1">{{ __("Apps") }}</span>
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
								<component :is="item.icon" class="h-icon-md w-icon-md" />
							</template>
							<template #badge>
								<ExternalLink class="flex-none text-ink-3" aria-hidden="true" />
							</template>
						</GListRow>
					</GListPanel>
				</template>
			</div>
		</template>
	</BaseLayout>
</template>

<script setup>
import { CalendarDays, ExternalLink, Users } from "lucide-vue-next"
import { useRouter } from "vue-router"
import { computed, inject, markRaw, ref } from "vue"

import BaseLayout from "@/components/BaseLayout.vue"
import HolidayList from "@/components/HolidayList.vue"
import GModal from "@/components/glass/GModal.vue"
import GListPanel from "@/components/glass/GListPanel.vue"
import GListRow from "@/components/glass/GListRow.vue"
import { MORE_ITEMS, visibleAppItems } from "@/data/navItems"
import { isSameOriginPath } from "@/data/appLinks"
import { hasTeam } from "@/data/team"
import { userResource } from "@/data/user"

const router = useRouter()
const employee = inject("$employee")
const holidaysOpen = ref(false)
const __ = inject("$translate")

// Team is manager-only: the entry appears once has_team confirms direct reports
// (or the caller is HR, who browse teams via the selector)
const moreItems = computed(() => {
	// Helpdesk (HR Issues + IT Helpdesk) is in MORE_ITEMS for everyone; the IT
	// pill inside it is what the Helpdesk-app availability gate hides now
	const items = MORE_ITEMS.map((item) => ({ ...item, title: __(item.title) }))
	if (hasTeam.data) {
		items.push({ icon: markRaw(Users), title: __("Team"), route: "/team" })
	}
	return items
})

// Role-gated (data/appLinks.js). An employee with neither the finance nor the
// projects roles gets no Apps group at all — the heading goes with the rows,
// because a labelled empty panel reads as a fault rather than as "not for you".
const appItems = computed(() =>
	visibleAppItems(userResource.data?.roles).map((item) => ({
		...item,
		title: __(item.title),
		sublabel: __(item.sublabel),
	}))
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
