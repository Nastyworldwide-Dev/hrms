<template>
	<GPage>
		<!-- The one header (alpha.5). "Mark all read" is this screen's own action,
		     in place of the bell and avatar (sketch: alpha5-review.html). -->
		<ShellHeader :title="__('Notifications')">
			<template #actions>
				<button
					v-if="unreadNotificationsCount.data"
					type="button"
					class="g-focusable g-touch px-2 text-sm font-semibold text-accent-ink bg-transparent border-none whitespace-nowrap"
					:disabled="markAllAsRead.loading"
					@click="markAllAsRead.submit()"
				>
					{{ __("Mark all read") }}
				</button>
			</template>
		</ShellHeader>
		<ion-content class="ion-padding g-page__content">
			<div class="flex flex-col min-h-full w-full">
				<div class="w-full max-w-content-column-lg mx-auto">
					<div class="flex flex-col gap-3 p-4">

						<GListPanel v-if="firstLoad" :loading="firstLoad" :rows="5" />

						<!-- One panel per day group: at most three (Today, Yesterday,
						     Earlier), so the screen stays inside the surface budget. -->
						<!-- glass-surfaces: bounded — three day groups at most -->
						<template v-for="group in groups" :key="group.key">
							<!-- The unread count rides on the first header ("Today · 3 unread"),
							     not a loose line above the list (alpha.9 D3; iOS section header). -->
							<h2 class="g-form-section__title mt-2">
								{{ groupTitle(group) }}
							</h2>
							<GListPanel>
								<GListRow
									v-for="item in group.items"
									:key="item.name"
									:class="{ 'n-unread': !item.read }"
									:label="item.line.title"
									:sublabel="item.meta"
									:tint="tileFor(item.reference_document_type)"
									:chevron="item.navigable && item.read"
									@click="open(item)"
								>
									<template #icon>
										<component :is="kindIcon(item)" class="g-row-icon" />
									</template>
									<template #badge>
										<span
											v-if="!item.read"
											class="flex-none w-2 h-2 rounded-full bg-accent"
											:aria-label="__('Unread')"
										/>
									</template>
								</GListRow>
							</GListPanel>
						</template>

						<div v-if="notifications.data?.length && notifications.hasNextPage" class="flex">
							<button
								type="button"
								class="g-focusable g-list-more w-full py-3 text-sm text-ink-600 bg-transparent border-none"
								@click="loadMore"
							>
								{{ __("Show more") }}
							</button>
						</div>
						<!-- Three states, each on its own condition (a loaded-but-empty
						     list once rendered NOTHING when the empty state was chained to
						     the list's v-if). -->
						<ResourceError :resource="notifications" what="your notifications" />
						<GEmptyState
							v-if="feedIsEmpty"
							:title="__('You are all caught up')"
							:body="__('New notifications will appear here')"
						/>
					</div>
				</div>
			</div>
		</ion-content>
	</GPage>
</template>

<script setup>
import { tileFor } from "@/utils/iconTile"
import dayjs from "dayjs"
import {
	Bell,
	CalendarCheck,
	CalendarClock,
	Clock,
	LifeBuoy,
	MapPin,
	Palmtree,
	Receipt,
} from "lucide-vue-next"
import GEmptyState from "@/components/glass/GEmptyState.vue"
import GListPanel from "@/components/glass/GListPanel.vue"
import GListRow from "@/components/glass/GListRow.vue"
import ResourceError from "@/components/ResourceError.vue"
import GPage from "@/components/glass/GPage.vue"
import { IonContent } from "@ionic/vue"
import { useRouter } from "vue-router"
import ShellHeader from "@/components/ShellHeader.vue"

import { notificationRoute } from "@/utils/notifications"
import { dayGroup, notificationLine } from "@/utils/notificationLine"
import { siteTime, siteTimeZone } from "@/utils/siteTime"
import { createResource, frappeRequest } from "frappe-ui"

import { computed, inject, onMounted, ref, watch } from "vue"

import { unreadNotificationsCount, notifications } from "@/data/notifications"

const router = useRouter()
const __ = inject("$translate")
const currentStart = ref(0)
const pageLength = 20
// "All caught up" only when the feed's request has actually answered empty:
// the list wrapper restores a cached (possibly empty) page before its request
// runs, and the request's own loading/error live on `.list`, not the wrapper.
const feedIsEmpty = computed(
	() =>
		notifications.list.fetched &&
		!notifications.list.loading &&
		!notifications.list.error &&
		!notifications.data?.length
)
// skeleton rows only while the FIRST page is on its way — a "Show more"
// keeps the rows already on screen
const firstLoad = computed(() => notifications.list.loading && !notifications.data?.length)

// Status of each Remote Checkin Request referenced by a visible notification,
// keyed by request docname. It only chooses the wording of the line.
const remoteRequestStatus = ref({})

// An approver may not READ Remote Checkin Request: a 403 here means "status
// unknown", never a toast over the feed — so this one bypasses the loud
// fetcher and the line falls back to the notification's own words.
const remoteRequestStatusResource = createResource({
	url: "frappe.client.get_list",
	resourceFetcher: frappeRequest,
	makeParams(values) {
		return {
			doctype: "Remote Checkin Request",
			filters: { name: ["in", values.names] },
			fields: ["name", "status"],
			limit_page_length: values.names.length,
		}
	},
	onSuccess(rows) {
		const next = { ...remoteRequestStatus.value }
		for (const row of rows || []) {
			next[row.name] = row.status
		}
		remoteRequestStatus.value = next
	},
	onError(error) {
		console.info("[Notifications] remote check-in status unknown:", error?.exc_type || error)
	},
})

function refreshRemoteStatuses() {
	const names = (notifications.data || [])
		.filter((n) => n.reference_document_type === "Remote Checkin Request")
		.map((n) => n.reference_document_name)
		.filter(Boolean)
	if (!names.length) {
		remoteRequestStatus.value = {}
		return
	}
	console.info("[Notifications] reading", names.length, "remote check-in status(es)")
	remoteRequestStatusResource.submit({ names })?.catch?.(() => {})
}

watch(() => notifications.data, refreshRemoteStatuses, { immediate: true })

const KIND_ICON = {
	"Leave Application": Palmtree,
	"Compensatory Leave Request": Palmtree,
	"Replacement Leave Claim": Palmtree,
	"OT Request": Clock,
	"Expense Claim": Receipt,
	"Shift Request": CalendarClock,
	"Attendance Request": CalendarCheck,
	"Employee Issue": LifeBuoy,
	"HD Ticket": LifeBuoy,
	"Remote Checkin Request": MapPin,
}
//: The kind's colour, as on Home and Requests (alpha.9 D24; alpha.7 §7).
//: Unread rows carry the dot, read rows the chevron: iOS Mail shows one mark
//: at the trailing edge, never both.
const kindIcon = (item) => KIND_ICON[item.reference_document_type] || Bell

// Today / Yesterday / Earlier on the SITE clock. Each row carries its short
// line (utils/notificationLine.js) and "who · when"; the stored sentence is
// never drawn.
const GROUPS = { Today: "Today", Yesterday: "Yesterday", Earlier: "Earlier" }
//: The first section header carries the unread count (alpha.9 D3).
function groupTitle(group) {
	const unread = Number(unreadNotificationsCount.data) || 0
	return group === groups.value[0] && unread ? __("{0} · {1} unread", [group.label, unread]) : group.label
}

const groups = computed(() => {
	const now = dayjs().tz(siteTimeZone())
	const out = []
	for (const item of notifications.data || []) {
		const key = dayGroup(siteTime(item.creation), now)
		const when = siteTime(item.creation)
		let group = out.find((g) => g.key === key)
		if (!group) {
			group = { key, label: __(GROUPS[key]), items: [] }
			out.push(group)
		}
		const line = notificationLine(item, {
			t: __,
			remoteStatus: remoteRequestStatus.value[item.reference_document_name],
		})
		const time = when.isValid() ? when.format(key === "Earlier" ? "ddd D MMM" : "h:mm a") : ""
		group.items.push({
			...item,
			line,
			meta: [line.who, time].filter(Boolean).join(" · "),
			navigable: Boolean(getItemRoute(item)),
			source: item,
		})
	}
	console.info("[Notifications] grouped", notifications.data?.length || 0, "row(s) into", out.length)
	return out
})

const markAllAsRead = createResource({
	url: "hrms.api.mark_all_notifications_as_read",
	onSuccess() {
		notifications.reload()
	},
})

// Through the to_user-scoped endpoint, never frappe.client.set_value: staff
// hold READ on PWA Notification and nothing else, so the direct write 403'd on
// every tap — a "Not permitted" toast over the opened screen and an unread
// count that only grew. Pinned by tests/notification-mark-read.test.mjs.
const markNotificationAsRead = createResource({
	url: "hrms.api.mark_notification_as_read",
})

function markAsRead(item) {
	if (item.read) return
	markNotificationAsRead.submit(
		{ name: item.name },
		{
			onSuccess: () => {
				item.read = 1
				unreadNotificationsCount.reload()
			},
		}
	)
}

// Route resolution lives in utils/notifications.js — pure and pinned by
// frontend/tests/notification-routing.test.mjs, because the derived-route
// contract has produced a silent dead tap once already.
function getItemRoute(item) {
	return notificationRoute(item, remoteRequestStatus.value[item.reference_document_name], (name) =>
		router.hasRoute(name)
	)
}

// A tap marks the row read and, when it refers to something reachable,
// opens it. Anything unroutable is a plain row, not a link to nowhere.
function open(row) {
	const route = getItemRoute(row.source)
	console.info("[Notifications] open", row.reference_document_type, route?.name || "(no route)")
	markAsRead(row.source)
	if (route) router.push(route)
}

onMounted(() => {
	currentStart.value = 0
	notifications.start = 0
	notifications.pageLength = pageLength
	notifications.fetch()
})

function loadMore() {
	currentStart.value += pageLength
	notifications.start = currentStart.value
	notifications.pageLength = pageLength
	notifications.list.fetch()
}
</script>

<!-- A local class, not a theme one: unread rows carry a bolder label. -->
<style scoped>
.n-unread :deep(.g-row__label) {
	font-weight: 600;
}
</style>
