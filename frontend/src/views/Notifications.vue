<template>
	<ion-page>
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
							<h2 class="font-sans font-extrabold text-lg tracking-tight text-inkbase">{{ __("Notifications") }}</h2>
						</div>
					</header>

					<div class="flex flex-col gap-4 mt-5 p-4">
						<div class="flex flex-row justify-between items-center">
							<div
								class="font-sans font-extrabold text-[22px] text-inkbase"
								v-if="unreadNotificationsCount.data"
							>
								{{ __("{0} Unread", [unreadNotificationsCount.data]) }}
							</div>
							<div class="flex ml-auto gap-1">
								<Button
									v-if="allowPushNotifications"
									variant="outline"
									@click="router.push({ name: 'Settings' })"
								>
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

						<div
							class="flex flex-col border-t-2 border-divider"
							v-if="notifications.data?.length"
						>
							<component
								:is="isRemoteRequestPending(item) ? 'div' : 'router-link'"
								:class="[
									'flex flex-row items-start p-4 justify-between border-b border-divider before:mt-2',
									`before:content-[''] before:mr-2 before:shrink-0 before:w-1.5 before:h-1.5`,
									item.read ? 'before:bg-transparent' : 'before:bg-accent',
								]"
								v-for="item in notifications.data"
								:key="item.name"
								:to="isRemoteRequestPending(item) ? null : getItemRoute(item)"
								@click="!isRemoteRequestPending(item) && markAsRead(item.name)"
							>
								<span class="m-avatar-sq grayscale shrink-0">
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
									<div
										v-else
										class="text-sm leading-5 font-normal text-ink-500 italic"
									>
										{{ fallbackMessage(item) }}
									</div>
									<div class="text-xs font-normal text-ink-600">
										{{ dayjs(item.creation).fromNow() }}
									</div>

									<!-- Inline approve/reject for pending Remote Checkin Requests.
									     Tapping either opens a remarks sheet so the approver
									     can leave a note before confirming, matching the
									     RemoteApprovals view. -->
									<div
										v-if="isRemoteRequestPending(item)"
										class="flex flex-row gap-2.5 mt-2"
									>
										<button
											class="flex-1 flex items-center justify-center bg-transparent border border-accent text-accent-700 px-3.5 py-2.5 font-sans font-extrabold text-xs hover:bg-accent-100"
											@click.stop.prevent="openDecision(item, 'reject')"
										>
											{{ __("Reject") }}
										</button>
										<button
											class="flex-1 flex items-center justify-center bg-accent text-ground px-3.5 py-2.5 font-sans font-extrabold text-xs hover:bg-accent-600"
											@click.stop.prevent="openDecision(item, 'approve')"
										>
											{{ __("Approve") }}
										</button>
									</div>
								</div>
							</component>

						</div>
						<div v-if="notifications.data?.length && notifications.hasNextPage" class="flex">
							<Button
								variant="outline"
								class="ml-auto"
								@click="loadMore"
							>
								{{ __('Load more') }}
							</Button>
						</div>
						<EmptyState v-else-if="!notifications.data" :message="__('You have no notifications')" />
					</div>
				</div>
			</div>
			<ion-modal
				:is-open="decisionOpen"
				@didDismiss="decisionOpen = false"
				:initial-breakpoint="1"
				:breakpoints="[0, 1]"
			>
				<div class="bg-ground w-full flex flex-col pb-8 max-h-[calc(100vh-5rem)] border-t-[3px] border-inkbase">
					<div class="flex flex-col gap-1.5 px-4 pt-6 pb-5">
						<span class="m-kicker">{{ __("Remote check-in") }}</span>
						<span class="font-sans font-extrabold text-[22px] text-inkbase">
							{{
								decisionKind === "approve"
									? __("Approve this check-in?")
									: __("Reject this check-in?")
							}}
						</span>
						<span class="text-xs text-ink-600">{{ activeItemLabel }}</span>
					</div>

					<div class="flex flex-col gap-1.5 px-4 pt-1">
						<label class="text-xs text-ink-700">
							{{ __("Remarks (optional)") }}
						</label>
						<textarea
							v-model="decisionRemarks"
							rows="3"
							maxlength="500"
							:placeholder="
								decisionKind === 'approve'
									? __('e.g. Approved — you were at the client site.')
									: __('e.g. Please retry from inside the office radius.')
							"
							class="w-full text-sm bg-surface border border-divider text-inkbase caret-accent p-2.5 resize-y outline-none focus:border-accent"
						/>
					</div>

					<div class="flex flex-row gap-2.5 px-4 pt-4">
						<button
							class="flex-1 flex items-center justify-center bg-transparent border border-divider text-inkbase px-3.5 py-3 font-sans font-extrabold text-[13px] hover:bg-ink-200 disabled:opacity-60"
							@click="decisionOpen = false"
							:disabled="decisionSubmitting"
						>
							{{ __("Cancel") }}
						</button>
						<button
							class="flex-1 flex items-center justify-center gap-2 bg-accent text-ground px-3.5 py-3 font-sans font-extrabold text-[13px] hover:bg-accent-600 disabled:opacity-60"
							:disabled="decisionSubmitting"
							@click="submitDecision"
						>
							<LoadingIndicator v-if="decisionSubmitting" class="w-4 h-4" />
							{{
								decisionKind === "approve"
									? __("Confirm Approve")
									: __("Confirm Reject")
							}}
						</button>
					</div>
				</div>
			</ion-modal>
		</ion-content>
	</ion-page>
</template>

<script setup>
import { IonContent, IonPage, IonModal } from "@ionic/vue"
import { useRouter } from "vue-router"

import { goBackOrHome } from "@/utils/navigation"
import { createResource, FeatherIcon, Button, LoadingIndicator, toast } from "frappe-ui"

import { computed, inject, onMounted, ref, watch } from "vue"
import EmployeeAvatar from "@/components/EmployeeAvatar.vue"
import EmptyState from "@/components/EmptyState.vue"

import {
	unreadNotificationsCount,
	notifications,
	arePushNotificationsEnabled,
} from "@/data/notifications"
import {
	approveResource,
	rejectResource,
	pendingCountResource,
} from "@/data/remoteCheckin"

const dayjs = inject("$dayjs")
const router = useRouter()
const __ = inject("$translate")
const currentStart = ref(0)
const pageLength = 10

// Status of each Remote Checkin Request referenced by a visible notification,
// keyed by request docname. Lets us hide Approve/Reject once the request is
// decided (whether the user acted here, in RemoteApprovals, or someone else
// raced them).
const remoteRequestStatus = ref({})

// Decision modal state — opened from the inline Approve/Reject buttons
// on a Remote Checkin Request notification card. Lets the approver
// leave optional remarks before confirming, matching RemoteApprovals.
const decisionOpen = ref(false)
const decisionKind = ref("approve") // 'approve' | 'reject'
const decisionRemarks = ref("")
const decisionSubmitting = ref(false)
const decisionTarget = ref(null) // the notification item being acted on

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

function isRemoteRequestPending(item) {
	return (
		item.reference_document_type === "Remote Checkin Request" &&
		remoteRequestStatus.value[item.reference_document_name] === "Pending"
	)
}

// Defensive: some legacy notification rows persisted with an empty
// message field (rich-text sanitiser stripped plain text). Render a
// derived label so the user at least sees what the row references.
function stripHtml(html) {
	if (!html) return ""
	return String(html).replace(/<[^>]*>/g, "").trim()
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


const allowPushNotifications = computed(
	() =>
		window.frappe?.boot.push_relay_server_url &&
		arePushNotificationsEnabled.data
)

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

function getItemRoute(item) {
	return {
		name: `${item.reference_document_type.replace(/\s+/g, "")}DetailView`,
		params: { id: item.reference_document_name },
	}
}

const activeItemLabel = computed(() => {
	const item = decisionTarget.value
	if (!item) return ""
	// Strip HTML for the modal subtitle since item.message is rich text.
	const plain = stripHtml(item.message)
	return plain || (item.reference_document_name || "")
})

function openDecision(item, kind) {
	if (!item?.reference_document_name) return
	decisionTarget.value = item
	decisionKind.value = kind
	decisionRemarks.value = ""
	decisionOpen.value = true
}

async function submitDecision() {
	const item = decisionTarget.value
	if (!item) return
	const requestName = item.reference_document_name
	const kind = decisionKind.value
	decisionSubmitting.value = true
	const resource = kind === "approve" ? approveResource : rejectResource
	try {
		await resource.submit({
			request: requestName,
			approver_remarks: decisionRemarks.value.trim(),
		})
		remoteRequestStatus.value = {
			...remoteRequestStatus.value,
			[requestName]: kind === "approve" ? "Approved" : "Rejected",
		}
		toast({
			title: kind === "approve" ? __("Approved") : __("Rejected"),
			text: __("The employee has been notified."),
			icon: "check-circle",
			position: "bottom-center",
			iconClasses: "text-green-500",
		})
		if (!item.read) {
			markAsRead(item.name)
		}
		pendingCountResource.reload?.()
		decisionOpen.value = false
	} catch (err) {
		console.error("[Notifications] decision failed:", err)
		toast({
			title: __("Could not save"),
			text: err?.messages?.[0] || __("Try again."),
			icon: "alert-circle",
			position: "bottom-center",
			iconClasses: "text-red-500",
		})
	} finally {
		decisionSubmitting.value = false
	}
}

onMounted(() => {
	notifications.start = 0,
	notifications.pageLength = 10,
	notifications.fetch()
})

function loadMore() {
	currentStart.value += pageLength
	notifications.start = currentStart.value
	notifications.pageLength = pageLength
	notifications.list.fetch()
}
</script>
