<!--
  Announcements — the Home block (revamp §3, owner's request 22 Sep 2026).

  The first thing 2.0 was asked for by name, and the one the old plan's "no new
  backend" rule made impossible to build. It is a BOARD, not a feed: HR posts a
  handful of things a month, each with an end date, and the block disappears
  when there is nothing live.

  TWO CARDS, then a link. Home's job is to answer "what do I do right now"
  (§2), and a block that grows without bound pushes the check-in button below
  the fold. The count of what is not shown is stated rather than implied, so
  nobody has to guess whether tapping through is worth it.

  ABSENCE IS THE EMPTY STATE, the same rule NeedsYou follows: a permanent
  "no announcements" card would be wrong most of the time and would cost the
  fold every day.

  ACKNOWLEDGEMENT is the one thing here that is not passive. A card HR marked
  as needing it carries a button, stays at the top, and does not go away by
  being scrolled past — which is the entire difference between publishing a
  policy and being able to say who read it.
-->
<template>
	<div v-if="cards.length" class="w-full">
		<div class="g-eyebrow mb-4">{{ __("Announcements") }}</div>
		<GListPanel>
			<GListRow
				v-for="card in cards"
				:key="card.name"
				:label="card.title"
				:sublabel="subtitle(card)"
				@click="open(card)"
			>
				<template #icon>
					<component :is="iconFor(card.category)" class="g-row-icon" />
				</template>
				<template v-if="badgeFor(card)" #badge>
					<!-- A WORD, not a coloured dot. §14.1: colour may never be the
					     only signal, and "New" is also what a person would say. One
					     badge at a time — an unread policy is both new and waiting,
					     and the confirmation is the one that needs doing. -->
					<GBadge :variant="badgeFor(card).variant">{{ badgeFor(card).text }}</GBadge>
				</template>
			</GListRow>
		</GListPanel>

		<button
			v-if="more > 0"
			type="button"
			class="g-focusable g-list-more w-full py-3 text-sm text-ink-600 bg-transparent border-none"
			@click="router.push({ name: 'Announcements' })"
		>
			{{ __("See {0} more", [more]) }}
		</button>

		<!-- The board changes without the employee doing anything. Polite, not
		     an alert: a new notice is not worth interrupting a sentence for. -->
		<p class="sr-only" role="status">{{ liveText }}</p>
	</div>
</template>

<script setup>
import { computed, inject, onMounted } from "vue"
import { useRouter } from "vue-router"
import { CalendarDays, Megaphone, ShieldAlert, TriangleAlert } from "lucide-vue-next"

import GListPanel from "@/components/glass/GListPanel.vue"
import GListRow from "@/components/glass/GListRow.vue"
import GBadge from "@/components/glass/GBadge.vue"

import { homeAnnouncements } from "@/data/announcements"

const __ = inject("$translate")
const $dayjs = inject("$dayjs")
const router = useRouter()

//: The category's only job. It picks an icon and nothing else — the wire value
//: is a doctype Select, so it is MAPPED rather than translated: `__(category)`
//: renders the raw English word, because translation files do not contain a
//: doctype's own options. The OT compensation row and the attendance chip both
//: carried that defect this month.
const ICONS = {
	Notice: Megaphone,
	Policy: ShieldAlert,
	Event: CalendarDays,
	Urgent: TriangleAlert,
}

const cards = computed(() => homeAnnouncements.data?.announcements || [])
const more = computed(() => Number(homeAnnouncements.data?.more) || 0)

function iconFor(category) {
	return ICONS[category] || Megaphone
}

function badgeFor(card) {
	if (card.needs_acknowledgement) return { variant: "open", text: __("Confirm") }
	if (!card.read) return { variant: "accent", text: __("New") }
	return null
}

function subtitle(card) {
	// What the reader needs to decide whether to open it: whether it wants
	// something from them, and how old it is. Not the category — the icon
	// already says that, and saying it twice spends the line.
	if (card.needs_acknowledgement) return __("Needs your confirmation")
	return card.publish_from ? $dayjs(card.publish_from).fromNow() : ""
}

function open(card) {
	router.push({ name: "AnnouncementDetail", params: { id: card.name } })
}

const liveText = computed(() => {
	const unread = Number(homeAnnouncements.data?.unread) || 0
	return unread ? __("{0} unread announcement(s)", [unread]) : ""
})

onMounted(() => {
	homeAnnouncements.fetch()
})
</script>
