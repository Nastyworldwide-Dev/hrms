<template>
	<GPage>
		<ion-content class="ion-padding">
			<div class="flex flex-col h-screen w-screen bg-ground">
				<div class="w-full max-w-[620px] mx-auto">
					<header
						class="flex flex-row bg-ground py-3.5 px-4 items-center justify-between border-b-2 border-divider sticky top-0 z-10"
					>
						<div class="flex flex-row items-center gap-2.5">
							<Button
								variant="ghost"
								class="!pl-0 hover:bg-transparent"
								@click="goBackOrHome(router)"
							>
								<FeatherIcon name="arrow-left" class="h-5 w-5" />
							</Button>
							<h2 class="font-sans font-extrabold text-lg tracking-tight text-inkbase">
								{{ __("Notifications") }}
							</h2>
						</div>
					</header>

					<div class="flex flex-col gap-4 mt-5 p-4">
						<div class="flex flex-row justify-between items-center">
							<div
								class="font-sans font-extrabold text-stat-number text-inkbase"
								v-if="unreadNotificationsCount.data"
							>
								{{ __("{0} Unread", [unreadNotificationsCount.data]) }}
							</div>
							<div class="flex ml-auto gap-1">
								<Button variant="outline" @click="router.push({ name: 'Settings' })">
									<template #prefix>
										<FeatherIcon name="settings" class="w-4" />
									</template>
									{{ __("Settings") }}
								</Button>
								<Button
									v-if="unreadNotificationsCount.data"
									variant="outline"
									@click="markAllAsRead.submit"
									:loading="markAllAsRead.loading"
								>
									<template #prefix>
										<FeatherIcon name="check-circle" class="w-4" />
									</template>
									{{ __("Mark all as read") }}
								</Button>
							</div>
						</div>

						<div class="flex flex-col border-t-2 border-divider" v-if="notifications.data?.length">
							<component
								:is="isItemNavigable(item) ? 'router-link' : 'div'"
								:class="[
									'flex flex-row items-start p-4 justify-between border-b border-divider before:mt-2',
									`before:content-[''] before:mr-2 before:shrink-0 before:w-1.5 before:h-1.5`,
									item.read ? 'before:bg-transparent' : 'before:bg-accent',
								]"
								v-for="item in notifications.data"
								:key="item.name"
								:to="isItemNavigable(item) ? getItemRoute(item) : null"
								@click="markAsRead(item.name)"
							>
								<span class="grayscale shrink-0">
									<EmployeeAvatar :userID="item.from_user" size="lg" />
								</span>
								<div class="flex flex-col gap-0.5 grow ml-3">
									<div
										v-if="item.message && stripHtml(item.message)"
										:class="[
											'text-sm leading-5',
											item.read ? 'font-normal text-ink-700' : 'font-medium text-inkbase',
										]"
										v-html="item.message"
									></div>
									<div v-else class="text-sm leading-5 font-normal text-ink-500 italic">
										{{ fallbackMessage(item) }}
									</div>
									<div class="text-xs font-normal text-ink-600">
										{{ dayjs(item.creation).fromNow() }}
									</div>
								</div>
							</component>
						</div>
						<div v-if="notifications.data?.length && notifications.hasNextPage" class="flex">
							<Button variant="outline" class="ml-auto" @click="loadMore">
								{{ __("Load more") }}
							</Button>
						</div>
						<EmptyState
							v-else-if="!notifications.data"
							:message="__('You have no notifications')"
						/>
					</div>
				</div>
			</div>
		</ion-content>
	</GPage>
</template>

<script setup>
import GPage from "@/components/glass/GPage.vue"
import { IonContent} from "@ionic/vue"
import { useRouter } from "vue-router"

import { goBackOrHome } from "@/utils/navigation"
import { notificationRoute } from "@/utils/notifications"
import { createResource, FeatherIcon, Button } from "frappe-ui"

import { inject, onMounted, ref, watch } from "vue"
import EmployeeAvatar from "@/components/EmployeeAvatar.vue"
import EmptyState from "@/components/EmptyState.vue"

import { unreadNotificationsCount, notifications } from "@/data/notifications"

const dayjs = inject("$dayjs")
const router = useRouter()
const __ = inject("$translate")
const currentStart = ref(0)
const pageLength = 10

// Status of each Remote Checkin Request referenced by a visible notification,
// keyed by request docname. Decides where the tap lands (pending -> the
// approvals queue, decided -> its History entry) and what the fallback
// message says. The buttons themselves live on RemoteApprovals: notifications
// notify, they do not act.
const remoteRequestStatus = ref({})

const remoteRequestStatusResource = createResource({
	url: "frappe.client.get_list",
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
	remoteRequestStatusResource.submit({ names })
}

watch(() => notifications.data, refreshRemoteStatuses, { immediate: true })

// Defensive: some legacy notification rows persisted with an empty
// message field (rich-text sanitiser stripped plain text). Render a
// derived label so the user at least sees what the row references.
function stripHtml(html) {
	if (!html) return ""
	return String(html)
		.replace(/<[^>]*>/g, "")
		.trim()
}

function fallbackMessage(item) {
	const docType = item.reference_document_type || __("Notification")
	const status = remoteRequestStatus.value[item.reference_document_name]
	if (item.reference_document_type === "Remote Checkin Request") {
		if (status === "Pending") return __("Remote check-in awaiting your decision.")
		if (status === "Approved") return __("Remote check-in approved.")
		if (status === "Rejected") return __("Remote check-in rejected.")
		return __("Remote check-in update.")
	}
	return __("New {0}", [docType])
}

const markAllAsRead = createResource({
	url: "hrms.api.mark_all_notifications_as_read",
	onSuccess() {
		notifications.reload()
	},
})

function markAsRead(name) {
	notifications.setValue.submit(
		{ name, read: 1 },
		{
			onSuccess: () => {
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

// Anything unroutable renders as plain content rather than a link to nowhere.
function isItemNavigable(item) {
	return Boolean(getItemRoute(item))
}

onMounted(() => {
	;(notifications.start = 0), (notifications.pageLength = 10), notifications.fetch()
})

function loadMore() {
	currentStart.value += pageLength
	notifications.start = currentStart.value
	notifications.pageLength = pageLength
	notifications.list.fetch()
}
</script>
