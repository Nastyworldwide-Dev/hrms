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
				class="flex flex-col gap-4 px-4 pt-6 pb-8 w-full max-w-content-column-read mx-auto lg:py-7"
			>
				<ResourceError :resource="announcementDetail" record back what="this announcement" />

				<template v-if="announcementDetail.loading && !doc">
					<GSkeleton height="24px" width="70%" />
					<GSkeleton height="220px" />
				</template>

				<template v-else-if="doc">
					<!-- HR's "Preview as staff" (alpha.7 4.2): the real screen,
					     marked, and nothing is recorded. -->
					<GBanner v-if="preview" variant="warning">
						{{
							doc.published === false
								? __("Preview — not published to anyone yet")
								: __("Preview — as staff will see it")
						}}
					</GBanner>
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
					<!-- the end of the text: reaching it opens the tick (owner, 19 Oct 2026) -->
					<div ref="endMarker" class="g-mustread__end" aria-hidden="true" />

					<GBanner v-if="acknowledged" variant="info">
						{{ __("You confirmed you read this.") }}
					</GBanner>

					<!-- The same gate as the full-screen must-read: read to the end,
					     tick "I have read and understood this" (a statement the person
					     makes, not a dismissal), then Confirm. -->
					<template v-else-if="doc.acknowledge_required && !preview">
						<GCheckbox
							v-model="ticked"
							:label="__('I have read and understood this')"
							:disabled="!state.canTick"
							:described-by="`announcement-confirm-${id}`"
						/>
						<GButton
							:label="__(state.label)"
							:class="{ 'g-mustread__waiting': !state.ready }"
							@click="confirm"
						/>
						<!-- what is missing, said when it changes (the tick opening, Confirm ready). One id per
						     notice: Ionic keeps the previous notice's page in the DOM (review of 808741bbc). -->
						<span :id="`announcement-confirm-${id}`" class="sr-only" aria-live="polite">{{
							__(state.label)
						}}</span>
					</template>

					<!-- after the body and its confirm: the nudge never stands between a
					     person and what they must read (owner, 19 Oct 2026) -->
					<PushNudge v-if="!preview" />
				</template>
			</div>
		</template>
	</BaseLayout>
</template>

<script setup>
import { computed, inject, nextTick, onBeforeUnmount, ref, watch } from "vue"
import { useRoute } from "vue-router"
import { CalendarDays, Megaphone, ShieldAlert, TriangleAlert } from "lucide-vue-next"

import BaseLayout from "@/components/BaseLayout.vue"
import PushNudge from "@/components/PushNudge.vue"
import ResourceError from "@/components/ResourceError.vue"
import GBanner from "@/components/glass/GBanner.vue"
import GButton from "@/components/glass/GButton.vue"
import GCheckbox from "@/components/glass/GCheckbox.vue"
import GSkeleton from "@/components/glass/GSkeleton.vue"
import { gToast } from "@/components/glass/toast"

import { confirmState } from "@/utils/mustRead"
import { safeHtml } from "@/utils/safeHtml"
import {
	acknowledgeAnnouncement,
	announcementDetail,
	reloadAnnouncements,
} from "@/data/announcements"

const props = defineProps({ id: { type: String, required: true } })
const route = useRoute()
const preview = computed(() => route.query.preview === "1")

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

const endMarker = ref(null)
const reachedEnd = ref(false)
const ticked = ref(false)
const state = computed(() =>
	confirmState({
		reachedEnd: reachedEnd.value,
		pending: acknowledgeAnnouncement.loading,
		failed: Boolean(announcementDetail.error),
		ticked: ticked.value,
	})
)
//: Rooted on the viewport: the page scrolls inside BaseLayout's ion-content, and the
//: marker entering the screen is the same fact either way.
//: Re-armed for EACH notice once its own text is on screen: a reused marker is not observed
//: again, and the shared resource can still hold the last notice's text for a frame, so a
//: short notice before a long one must not open the tick unread (review of a2f27ddb3).
let observer = null
function watchEnd() {
	observer?.disconnect()
	if (!endMarker.value || typeof IntersectionObserver === "undefined") return
	observer = new IntersectionObserver((entries) => {
		if (doc.value?.name === props.id && entries.some((e) => e.isIntersecting))
			reachedEnd.value = true
	})
	observer.observe(endMarker.value)
}
watch(
	() => [endMarker.value, doc.value?.name === props.id],
	async ([marker, shown]) => {
		if (!marker || !shown) return
		await nextTick()
		watchEnd()
	}
)
onBeforeUnmount(() => observer?.disconnect())

async function confirm() {
	if (!reachedEnd.value) {
		// never a dead button: it takes the reader to the end
		endMarker.value?.scrollIntoView?.({ behavior: "smooth", block: "end" })
		return
	}
	// read to the end, not yet ticked: the label says so; nothing is recorded
	if (!state.value.ready) return
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
		// each notice is read and ticked for itself
		reachedEnd.value = false
		ticked.value = false
		// Fetching is what marks it read, which is why this runs on every
		// open rather than only when the payload is missing.
		announcementDetail.fetch({ name: id, preview: preview.value ? 1 : 0 })
	},
	{ immediate: true }
)
</script>
