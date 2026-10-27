<!--
  The full announcement board (revamp §3).

  Home shows two; this is the rest. It is a LIST rather than a feed of full
  cards: an employee arriving here is usually looking for one thing they half
  remember, and eight expanded bodies is a scroll rather than a board.

  Grouped into "To confirm" and "Latest", because those are two different jobs.
  A policy waiting for confirmation is a task; everything else is reading, urgent
  first. Every row is the Home row (red tile, HR's summary, Confirm / Urgent /
  New), drawn by the one rule in utils/announcementRow.js, with its age on the
  right (owner-approved mockup, 27 Oct 2026).
-->
<template>
	<BaseLayout :pageTitle="__('Announcements')">
		<template #body>
			<GPullRefresh @refresh="refresh" />
			<div
				class="flex flex-col gap-4 px-4 pt-6 pb-8 w-full max-w-content-column-lg mx-auto lg:py-7"
			>
				<ResourceError :resource="allAnnouncements" what="announcements" />
				<PushNudge />

				<GListPanel v-if="allAnnouncements.loading && !rows.length" loading />

				<template v-else>
					<section v-for="group in groups" :key="group.key" class="flex flex-col gap-2">
						<h2 class="g-eyebrow ml-4">{{ group.title }}</h2>
						<GListPanel>
							<GListRow
								v-for="card in group.rows"
								:key="card.name"
								:label="card.title"
								:sublabel="subline(card)"
								:tint="TILE.announcement"
								@click="open(card)"
							>
								<template #icon>
									<component :is="iconFor(card.category)" class="g-row-icon" />
								</template>
								<template #badge>
									<!-- A WORD over the age, right aligned: the badge says what to do,
									     the age says how old it is. -->
									<span
										v-if="badge(card) || age(card)"
										class="flex flex-col items-end gap-0.5 shrink-0"
									>
										<template v-if="badge(card)">
											<span v-if="badge(card).variant === 'urgent'" class="g-badge g-chip--danger">
												{{ badge(card).text }}
											</span>
											<GBadge v-else :variant="badge(card).variant">{{ badge(card).text }}</GBadge>
										</template>
										<span v-if="age(card)" class="text-caption text-ink-700 whitespace-nowrap">{{
											age(card)
										}}</span>
									</span>
								</template>
							</GListRow>
						</GListPanel>
					</section>

					<!-- Not on error: ResourceError above already says what happened, and
					     "nothing live" beside "could not load" is two opposite claims. -->
					<GEmptyState
						v-if="!rows.length && !allAnnouncements.error"
						:title="__('Nothing on the board')"
						:body="__('Notices from HR appear here. There is nothing live at the moment.')"
					/>
				</template>
			</div>
		</template>
	</BaseLayout>
</template>

<script setup>
import { siteTime } from "@/utils/siteTime"
import PushNudge from "@/components/PushNudge.vue"
import { computed, defineAsyncComponent, inject, onMounted } from "vue"
import { useRouter } from "vue-router"
import { CalendarDays, Megaphone, ShieldAlert, TriangleAlert } from "lucide-vue-next"

import BaseLayout from "@/components/BaseLayout.vue"
import ResourceError from "@/components/ResourceError.vue"
import GBadge from "@/components/glass/GBadge.vue"
import GEmptyState from "@/components/glass/GEmptyState.vue"
import GListPanel from "@/components/glass/GListPanel.vue"
import GListRow from "@/components/glass/GListRow.vue"
//: Loaded on first use, not in the first download (alpha.13: Ionic's
//: refresher is 41 KB, and nobody pulls before the page has drawn).
const GPullRefresh = defineAsyncComponent(() => import("@/components/glass/GPullRefresh.vue"))

import { allAnnouncements } from "@/data/announcements"
import { badgeFor, boardSections, subtitle, trailAge } from "@/utils/announcementRow"
import { TILE } from "@/utils/iconTile"

const __ = inject("$translate")
const router = useRouter()

//: Mapped, never `__(category)`: a doctype Select value is not in the
//: translation files, so translating it renders the raw English word.
const ICONS = {
	Notice: Megaphone,
	Policy: ShieldAlert,
	Event: CalendarDays,
	Urgent: TriangleAlert,
}

const rows = computed(() => allAnnouncements.data?.announcements || [])
const sections = computed(() => boardSections(rows.value))
//: A section with nothing in it draws nothing, not a heading over an empty panel.
const groups = computed(() =>
	[
		{
			key: "confirm",
			title: `${__("To confirm")} · ${sections.value.toConfirm.length}`,
			rows: sections.value.toConfirm,
		},
		{ key: "latest", title: __("Latest"), rows: sections.value.latest },
	].filter((group) => group.rows.length)
)

function iconFor(category) {
	return ICONS[category] || Megaphone
}

//: The age on the site's clock, as the board has always read it.
const ageOf = (date) => siteTime(date).fromNow()
const badge = (card) => badgeFor(card, __)
const subline = (card) => subtitle(card, __, ageOf)
const age = (card) => trailAge(card, __, ageOf)

function open(card) {
	router.push({ name: "AnnouncementDetail", params: { id: card.name } })
}

async function refresh(event) {
	console.info("[Announcements] pull-to-refresh")
	await allAnnouncements.fetch()?.catch?.(() => {})
	event.target?.complete?.()
}

onMounted(() => {
	allAnnouncements.fetch()
})
</script>
