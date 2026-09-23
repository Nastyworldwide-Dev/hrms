<!--
  The full announcement board (revamp §3).

  Home shows two; this is the rest. It is a LIST rather than a feed of full
  cards: an employee arriving here is usually looking for one thing they half
  remember, and eight expanded bodies is a scroll rather than a board.

  Grouped into "needs you" and the rest, because those are two different jobs.
  A policy waiting for confirmation is a task; everything else is reading.
-->
<template>
	<BaseLayout :pageTitle="__('Announcements')">
		<template #body>
			<GPullRefresh @refresh="refresh" />
			<div
				class="flex flex-col gap-4 px-4 pt-6 pb-8 w-full max-w-content-column-lg mx-auto lg:p-7"
			>
				<ResourceError :resource="allAnnouncements" what="announcements" />

				<GListPanel v-if="allAnnouncements.loading && !rows.length" loading />

				<template v-else>
					<template v-if="needsYou.length">
						<div class="g-eyebrow">{{ __("Needs your confirmation") }}</div>
						<GListPanel>
							<GListRow
								v-for="card in needsYou"
								:key="card.name"
								:label="card.title"
								:sublabel="when(card)"
								@click="open(card)"
							>
								<template #icon>
									<component :is="iconFor(card.category)" class="g-row-icon" />
								</template>
								<template #badge>
									<GBadge variant="open">{{ __("Confirm") }}</GBadge>
								</template>
							</GListRow>
						</GListPanel>
					</template>

					<template v-if="rest.length">
						<div v-if="needsYou.length" class="g-eyebrow">
							{{ __("Everything else") }}
						</div>
						<GListPanel>
							<GListRow
								v-for="card in rest"
								:key="card.name"
								:label="card.title"
								:sublabel="when(card)"
								@click="open(card)"
							>
								<template #icon>
									<component :is="iconFor(card.category)" class="g-row-icon" />
								</template>
								<template v-if="!card.read" #badge>
									<GBadge variant="accent">{{ __("New") }}</GBadge>
								</template>
							</GListRow>
						</GListPanel>
					</template>

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
import { computed, inject, onMounted } from "vue"
import { useRouter } from "vue-router"
import { CalendarDays, Megaphone, ShieldAlert, TriangleAlert } from "lucide-vue-next"

import BaseLayout from "@/components/BaseLayout.vue"
import ResourceError from "@/components/ResourceError.vue"
import GBadge from "@/components/glass/GBadge.vue"
import GEmptyState from "@/components/glass/GEmptyState.vue"
import GListPanel from "@/components/glass/GListPanel.vue"
import GListRow from "@/components/glass/GListRow.vue"
import GPullRefresh from "@/components/glass/GPullRefresh.vue"

import { allAnnouncements } from "@/data/announcements"

const __ = inject("$translate")
const $dayjs = inject("$dayjs")
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
const needsYou = computed(() => rows.value.filter((card) => card.needs_acknowledgement))
const rest = computed(() => rows.value.filter((card) => !card.needs_acknowledgement))

function iconFor(category) {
	return ICONS[category] || Megaphone
}

function when(card) {
	return card.publish_from ? $dayjs(card.publish_from).fromNow() : ""
}

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
