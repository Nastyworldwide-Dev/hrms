<!--
  The must-read flow (alpha.7 plan §4.4/4.5, §10.3; the senior's goal:
  "make sure people read announcements").

  On app open, each notice HR marked must-read and this person has not yet
  confirmed (in this wording) opens FULL SCREEN, urgent first then oldest.
  The confirm button waits until the end is reached (IntersectionObserver on a
  marker after the body); before that it stays focusable, says "Read to the end
  to confirm", and a tap scrolls to the end, so VoiceOver users are never
  stuck. A non-urgent notice can be put off with "Remind me later" (this
  session); an urgent one cannot. Nothing here is hand-rolled: Ionic's modal
  (no swipe-to-dismiss), the browser's observer, the app's sanitiser.
-->
<template>
	<ion-modal
		:is-open="Boolean(current)"
		class="g-mustread"
		:can-dismiss="false"
		:backdrop-dismiss="false"
		:handle="false"
	>
		<div v-if="current" class="g-mustread__page" role="dialog" aria-modal="true" :aria-label="current.title">
			<header class="g-mustread__bar">
				<span class="g-mustread__tag">{{ current.urgent ? __("Urgent · must read") : __("Must read") }}</span>
			</header>
			<div ref="scroller" class="g-mustread__scroll">
				<h1 class="g-mustread__title">{{ current.title }}</h1>
				<p v-if="current.summary" class="g-mustread__summary">{{ current.summary }}</p>
				<div v-if="detail.loading && !body" class="g-mustread__loading">
					<GSkeleton height="220px" />
				</div>
				<div v-else class="prose-sm text-inkbase g-mustread__body" v-html="safeHtml(body)" />
				<div ref="endMarker" class="g-mustread__end" aria-hidden="true" />
			</div>
			<footer class="g-mustread__foot">
				<GButton
					:label="__(state.label)"
					:class="{ 'g-mustread__waiting': !state.ready }"
					@click="onConfirm"
				/>
				<button
					v-if="!Number(current.urgent)"
					type="button"
					class="g-mustread__later g-focusable"
					@click="later"
				>
					{{ __("Remind me later") }}
				</button>
			</footer>
		</div>
	</ion-modal>
</template>

<script setup>
import { computed, inject, nextTick, onBeforeUnmount, onMounted, ref, watch } from "vue"
import { IonModal } from "@ionic/vue"
import { createResource } from "frappe-ui"

import GButton from "@/components/glass/GButton.vue"
import GSkeleton from "@/components/glass/GSkeleton.vue"
import { gToast } from "@/components/glass/toast"
import { acknowledgeAnnouncement, reloadAnnouncements } from "@/data/announcements"
import { sessionUser } from "@/data/session"
import { confirmState, nextMustRead } from "@/utils/mustRead"
import { safeHtml } from "@/utils/safeHtml"

const __ = inject("$translate")

const queue = createResource({ url: "hrms.api.announcements.must_read", auto: false })
//: The body comes from get_announcement, which also records the read.
const detail = createResource({ url: "hrms.api.announcements.get_announcement", auto: false })

const snoozed = ref(new Set())
const current = computed(() => nextMustRead(queue.data, snoozed.value))
const body = computed(() => (detail.data?.name === current.value?.name ? detail.data.body : ""))

const reachedEnd = ref(false)
const pending = ref(false)
const state = computed(() => confirmState({ reachedEnd: reachedEnd.value, pending: pending.value }))

const scroller = ref(null)
const endMarker = ref(null)
let observer = null

function watchEnd() {
	observer?.disconnect()
	reachedEnd.value = false
	if (!endMarker.value || !scroller.value) return
	observer = new IntersectionObserver(
		(entries) => {
			if (entries.some((e) => e.isIntersecting)) reachedEnd.value = true
		},
		{ root: scroller.value, threshold: 1 }
	)
	observer.observe(endMarker.value)
}

watch(
	() => current.value?.name,
	async (name) => {
		if (!name) return
		console.info("[MustRead] opening", name)
		await detail.fetch({ name })?.catch?.(() => {})
		await nextTick()
		scroller.value?.scrollTo?.({ top: 0 })
		watchEnd()
	}
)

async function onConfirm() {
	if (pending.value) return
	if (!reachedEnd.value) {
		// Never a dead button: it takes the reader to the end.
		endMarker.value?.scrollIntoView?.({ behavior: "smooth", block: "end" })
		return
	}
	pending.value = true
	try {
		await acknowledgeAnnouncement.submit({ name: current.value.name })
		console.info("[MustRead] confirmed", current.value.name)
		await queue.reload()
		await reloadAnnouncements("must-read confirmed")
	} catch (error) {
		console.error("[MustRead] confirm failed", error)
		gToast({ title: __("Could not record that"), text: __("Try again in a moment."), variant: "error" })
	} finally {
		pending.value = false
	}
}

function later() {
	console.info("[MustRead] later", current.value?.name)
	snoozed.value = new Set([...snoozed.value, current.value.name])
}

onMounted(() => {
	if (sessionUser()) queue.fetch()?.catch?.(() => console.warn("[MustRead] queue unavailable"))
})
onBeforeUnmount(() => observer?.disconnect())
</script>
