<template>
	<BaseLayout :pageTitle="__('More')">
		<template #body>
			<div
				class="flex flex-col gap-3 w-full max-w-content-column-lg mx-auto px-4 pt-4 pb-4 lg:py-7"
			>
				<!-- one glass surface for the whole list (§15.1): the panel and its
				     rows count as ONE, not one per row -->
				<GListPanel>
					<GListRow
						v-for="item in moreItems"
						:key="item.route"
						:label="item.title"
						:tint="item.tint"
						@click="router.push(item.route)"
					>
						<template #icon>
							<component :is="item.icon" class="h-icon-md w-icon-md" />
						</template>
					</GListRow>
					<!-- One list of the year ahead, in a sheet (PAGE-20): its only
					     door was inside the Leaves dashboard, which More no longer
					     lists. -->
					<GListRow
						:label="__('Public holidays')"
						:tint="TILE.holiday"
						@click="holidaysOpen = true"
					>
						<template #icon>
							<CalendarDays class="h-icon-md w-icon-md" />
						</template>
					</GListRow>
				</GListPanel>

				<GModal
					:is-open="holidaysOpen"
					:title="__('Public holidays')"
					@did-dismiss="holidaysOpen = false"
				>
					<HolidayList v-if="holidaysOpen && employee.data" />
				</GModal>

				<!-- What a leader does for others, in one group (alpha.14 O): it was
				     split between You (Approvals) and here (Team), with Roster only
				     inside Team. Each row appears when the server says it applies. -->
				<template v-if="teamItems.length">
					<span class="g-eyebrow mt-1">{{ __("Your team") }}</span>
					<GListPanel>
						<GListRow
							v-for="item in teamItems"
							:key="item.key"
							:label="item.title"
							:tint="TILE.team"
							@click="router.push(item.to)"
						>
							<template #icon>
								<component :is="item.icon" class="h-icon-md w-icon-md" />
							</template>
							<template v-if="item.badge" #badge>
								<GBadge variant="accent">{{ item.badge }}</GBadge>
							</template>
						</GListRow>
					</GListPanel>
				</template>

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

				<!-- Services outside this site (28 Sep 2026: TruTrip, for business
				     travel). Opens in a new tab; carries no session of ours. -->
				<span class="g-eyebrow mt-1">{{ __("Travel") }}</span>
				<GListPanel>
					<GListRow
						v-for="item in externalItems"
						:key="item.key"
						:label="item.title"
						:sublabel="item.sublabel"
						:tint="TILE.shift"
						:chevron="false"
						@click="openExternal(item)"
					>
						<template #icon>
							<Plane class="h-icon-md w-icon-md" />
						</template>
						<template #badge>
							<ExternalLink class="flex-none text-ink-3" aria-hidden="true" />
						</template>
					</GListRow>
				</GListPanel>
			</div>
		</template>
	</BaseLayout>
</template>

<script setup>
import { TILE } from "@/utils/iconTile"
import { HUB_PATH } from "@/utils/helpdeskHub"
import {
	CalendarDays,
	CalendarRange,
	ExternalLink,
	Plane,
	SquareCheck,
	Users,
} from "lucide-vue-next"
import { useRouter } from "vue-router"
import { computed, inject, markRaw, onMounted, ref } from "vue"

import BaseLayout from "@/components/BaseLayout.vue"
import HolidayList from "@/components/HolidayList.vue"
import GModal from "@/components/glass/GModal.vue"
import GListPanel from "@/components/glass/GListPanel.vue"
import GListRow from "@/components/glass/GListRow.vue"
import { MORE_ITEMS, visibleAppItems } from "@/data/navItems"
import { isSameOriginPath } from "@/data/appLinks"
import { EXTERNAL_LINKS, openExternal } from "@/data/externalLinks"
import { hasTeam, isApprover } from "@/data/team"
import { needsYouResource } from "@/data/needsYou"
import GBadge from "@/components/glass/GBadge.vue"
import { myApps } from "@/data/myApps"

const router = useRouter()
const employee = inject("$employee")
const holidaysOpen = ref(false)
const __ = inject("$translate")

//: One tile colour per destination (alpha.7 §7).
const MORE_TINT = {
	[HUB_PATH]: TILE.help,
	"/sop": TILE.sop,
	"/announcements": TILE.announcement,
}
const moreItems = computed(() => {
	// Helpdesk (HR Issues + IT Helpdesk) is in MORE_ITEMS for everyone; the IT
	// pill inside it is what the Helpdesk-app availability gate hides now
	const items = MORE_ITEMS.map((item) => ({
		...item,
		title: __(item.title),
		tint: MORE_TINT[item.route] || TILE.neutral,
	}))
	return items
})

//: Approvals, Team and Roster (alpha.14 O). The server decides each:
//: isApprover (anyone something is routed to), hasTeam (direct reports, or HR).
//: The Approvals number is everything waiting on you, as Home's Needs you.
const waitingOnYou = computed(
	() =>
		(Number(needsYouResource.data?.total) || 0) + (Number(needsYouResource.data?.checkins) || 0)
)
onMounted(() => {
	if (isApprover.data) needsYouResource.reload()
})
const teamItems = computed(() => [
	...(isApprover.data
		? [
				{
					key: "approvals",
					icon: markRaw(SquareCheck),
					title: __("Approvals"),
					to: { name: "Approvals" },
					badge: waitingOnYou.value ? String(waitingOnYou.value) : "",
				},
		  ]
		: []),
	...(hasTeam.data
		? [
				{ key: "team", icon: markRaw(Users), title: __("Team"), route: "/team", to: "/team" },
				{
					key: "roster",
					icon: markRaw(CalendarRange),
					title: __("Roster"),
					route: "/team/roster",
					to: "/team/roster",
				},
		  ]
		: []),
])

// Offered by the server (hrms.api.app_links; audit F-15). Every employee is offered Approva; someone
// the server offers nothing gets no Apps group at all — the heading goes with the rows,
// because a labelled empty panel reads as a fault rather than as "not for you".
const appItems = computed(() =>
	visibleAppItems(myApps.data).map((item) => ({
		...item,
		title: __(item.title),
		sublabel: __(item.sublabel),
	}))
)

const externalItems = EXTERNAL_LINKS.map((item) => ({
	...item,
	title: __(item.title),
	sublabel: __(item.sublabel),
}))

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
