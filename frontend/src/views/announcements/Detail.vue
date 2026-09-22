<!--
  One announcement, in full (revamp §3).

  Opening this screen IS the read event — there is no separate "mark as read"
  control, because a button asking somebody to confirm they have read a canteen
  notice is ceremony, and a server endpoint that marks something read without
  showing it is a door that can be called about an announcement the caller
  cannot see.

  ACKNOWLEDGEMENT is the exception, and it is deliberately a real button with a
  real sentence on it. "I've read and understood this" is a statement a person
  makes; "OK" is a dialog being dismissed. For a safety notice that difference
  is the whole feature.
-->
<template>
	<BaseLayout :pageTitle="__('Announcement')">
		<template #body>
			<div
				class="flex flex-col gap-4 px-4 pt-6 pb-8 w-full max-w-content-column-read mx-auto lg:p-7"
			>
				<ResourceError :resource="announcementDetail" back what="this announcement" />

				<template v-if="announcementDetail.loading && !doc">
					<GSkeleton height="24px" width="70%" />
					<GSkeleton height="220px" />
				</template>

				<template v-else-if="doc">
					<div class="flex items-center gap-3">
						<component :is="iconFor(doc.category)" class="h-icon-lg w-icon-lg text-ink-600" />
						<span class="g-eyebrow">{{ categoryLabel(doc.category) }}</span>
					</div>

					<h1 class="text-screen-title text-inkbase">{{ doc.title }}</h1>
					<p class="text-caption text-ink-600">{{ posted }}</p>

					<!-- Sanitised through the app's own allow-list as well as
					     server-side: this is rich text an author controls, and
					     safeHtml is the one place that decision lives. -->
					<div class="prose-sm text-inkbase" v-html="safeHtml(doc.body)" />

					<GBanner v-if="acknowledged" variant="info">
						{{ __("You confirmed you read this.") }}
					</GBanner>

					<!-- A real sentence, not "OK". "I've read and understood this"
					     is a statement a person makes; a dialog dismissal is not,
					     and for a safety notice that difference is the feature. -->
					<GButton
						v-else-if="doc.acknowledge_required"
						:label="__(`I've read and understood this`)"
						:pending="acknowledgeAnnouncement.loading"
						:pending-label="__('Recording…')"
						@click="confirm"
					/>
				</template>
			</div>
		</template>
	</BaseLayout>
</template>

<script setup>
import { computed, inject, ref, watch } from "vue"
import { CalendarDays, Megaphone, ShieldAlert, TriangleAlert } from "lucide-vue-next"

import BaseLayout from "@/components/BaseLayout.vue"
import ResourceError from "@/components/ResourceError.vue"
import GBanner from "@/components/glass/GBanner.vue"
import GButton from "@/components/glass/GButton.vue"
import GSkeleton from "@/components/glass/GSkeleton.vue"
import { gToast } from "@/components/glass/toast"

import { safeHtml } from "@/utils/safeHtml"
import {
	acknowledgeAnnouncement,
	announcementDetail,
	reloadAnnouncements,
} from "@/data/announcements"

const props = defineProps({ id: { type: String, required: true } })

const __ = inject("$translate")
const $dayjs = inject("$dayjs")

const ICONS = {
	Notice: Megaphone,
	Policy: ShieldAlert,
	Event: CalendarDays,
	Urgent: TriangleAlert,
}

//: The wire value is a doctype Select. Mapped, not translated — the
//: translation files do not contain a doctype's options, so `__(category)`
//: would render the raw word and the mapping would be invisible.
const CATEGORY_LABELS = {
	Notice: "Notice",
	Policy: "Policy",
	Event: "Event",
	Urgent: "Urgent",
}

const doc = computed(() => announcementDetail.data)
//: Local, because the server's copy is a snapshot from before the tap. Seeded
//: from the payload so a revisit shows the confirmed state without a refetch.
const justAcknowledged = ref(false)
const acknowledged = computed(() => justAcknowledged.value || Boolean(doc.value?.acknowledged))

const posted = computed(() =>
	doc.value?.publish_from ? $dayjs(doc.value.publish_from).format("D MMM YYYY") : ""
)

function iconFor(category) {
	return ICONS[category] || Megaphone
}

function categoryLabel(category) {
	return __(CATEGORY_LABELS[category] || "Notice")
}

async function confirm() {
	try {
		await acknowledgeAnnouncement.submit({ name: props.id })
		justAcknowledged.value = true
		// Home's block and the board both change: the card leaves the "needs
		// you" slot and its badge goes. Refreshing only one leaves the other
		// wrong until a full reload.
		await reloadAnnouncements("acknowledged")
		gToast({ title: __("Thanks — that's recorded."), variant: "success" })
	} catch (error) {
		console.error("[Announcement] acknowledge failed", error)
		gToast({
			title: __("Could not record that"),
			text: __("Try again in a moment."),
			variant: "error",
		})
	}
}

watch(
	() => props.id,
	(id) => {
		justAcknowledged.value = false
		// Fetching is what marks it read, which is why this runs on every
		// open rather than only when the payload is missing.
		announcementDetail.fetch({ name: id })
	},
	{ immediate: true }
)
</script>
