<template>
	<GPage>
		<ion-content class="ion-padding">
			<div class="flex flex-col min-h-full w-full">
				<div class="w-full max-w-[680px] mx-auto">
					<header
						class="flex flex-row py-3.5 px-4 items-center justify-between border-b-2 border-divider sticky top-0 z-sticky bg-ground"
					>
						<div class="flex flex-row items-center gap-2.5">
							<GIconButton :label="__('Back')" flush @click="router.back()">
								<FeatherIcon name="chevron-left" class="h-5 w-5" />
							</GIconButton>
							<h2 class="font-sans font-extrabold text-lg tracking-tight text-inkbase">
								{{ __("Remote Approvals") }}
							</h2>
						</div>
						<GIconButton :label="__('Refresh')" @click="reload">
							<FeatherIcon name="refresh-cw" class="h-4 w-4" />
						</GIconButton>
					</header>

					<div class="flex flex-col p-4 gap-4">
						<GSegmented :buttons="TAB_BUTTONS" v-model="activeTab" />

						<template v-if="activeTab === 'History'">
							<div v-if="decided.loading && !decided.data" class="flex flex-col gap-3">
								<div v-for="i in 3" :key="i" class="h-20 bg-ink-200 animate-pulse" />
							</div>
							<div
								v-else-if="!decided.data || decided.data.length === 0"
								class="flex flex-col gap-1 border-t-2 border-divider py-8 px-0.5"
							>
								<span class="font-sans font-extrabold text-sm text-inkbase">
									{{ __("No decisions yet") }}
								</span>
								<span class="text-xs text-ink-600">
									{{ __("Remote check-ins you approve or reject stay reviewable here.") }}
								</span>
							</div>
							<div
								v-else
								v-for="req in decided.data"
								:key="req.name"
								class="border border-divider rounded-panel p-3.5 flex flex-col gap-2"
							>
								<div class="flex flex-row items-center justify-between">
									<div class="font-sans font-extrabold text-button-label text-inkbase truncate">
										{{ req.employee_name || req.employee }}
									</div>
									<span
										class="g-eyebrow px-2 py-[3px]"
										:class="
											req.status === 'Approved'
												? 'border border-accent-ink text-accent-700'
												: 'bg-inkbase text-ground'
										"
									>
										{{ __(req.status) }} · {{ req.log_type }}
									</span>
								</div>
								<div class="flex flex-row items-center justify-between text-kra-label text-ink-600">
									<span>{{ formatTimestamp(req.checkin_time) }}</span>
									<span class="tabular-nums">{{ formatDistance(req.distance_m) }}</span>
								</div>
								<div
									v-if="req.approver_remarks"
									class="text-xs text-inkbase bg-surface border border-divider p-2.5"
								>
									{{ req.approver_remarks }}
								</div>
							</div>
						</template>

						<template v-else>
							<div v-if="pending.loading && !pending.data" class="flex flex-col gap-3">
								<div v-for="i in 3" :key="i" class="h-28 bg-ink-200 animate-pulse" />
							</div>

							<div
								v-else-if="!pending.data || pending.data.length === 0"
								class="flex flex-col gap-1 border-t-2 border-divider py-8 px-0.5"
							>
								<span class="font-sans font-extrabold text-sm text-inkbase">
									{{ __("Nothing to approve right now") }}
								</span>
								<span class="text-xs text-ink-600">
									{{ __("Remote check-ins from your team will show up here.") }}
								</span>
							</div>

							<div
								v-else
								v-for="req in pending.data"
								:key="req.name"
								class="border border-divider rounded-panel p-3.5 flex flex-col gap-2"
							>
								<div class="flex flex-row items-center justify-between">
									<div class="font-sans font-extrabold text-button-label text-inkbase truncate">
										{{ req.employee_name || req.employee }}
									</div>
									<span
										class="g-eyebrow px-2 py-[3px]"
										:class="
											req.log_type === 'IN'
												? 'bg-inkbase text-ground'
												: 'border border-accent-ink text-accent-700'
										"
									>
										{{ req.log_type }}
									</span>
								</div>
								<div class="flex flex-row items-center justify-between text-kra-label text-ink-600">
									<span>{{ formatTimestamp(req.checkin_time) }}</span>
									<span class="tabular-nums">{{ formatDistance(req.distance_m) }}</span>
								</div>
								<div
									v-if="req.employee_remarks"
									class="text-xs text-inkbase bg-surface border border-divider p-2.5"
								>
									{{ req.employee_remarks }}
								</div>
								<div v-else class="text-xs text-ink-500 italic">
									{{ __("No reason provided.") }}
								</div>
								<div class="flex flex-row gap-2.5 mt-1">
									<button
										class="flex-1 flex items-center justify-center bg-transparent border border-accent-ink text-accent-700 px-3.5 py-2.5 font-sans font-extrabold text-xs hover:bg-accent-100"
										@click="openDecision(req, 'reject')"
									>
										{{ __("Reject") }}
									</button>
									<button
										class="flex-1 flex items-center justify-center bg-accent-ink text-ground px-3.5 py-2.5 font-sans font-extrabold text-xs hover:bg-accent-600"
										@click="openDecision(req, 'approve')"
									>
										{{ __("Approve") }}
									</button>
								</div>
							</div>
						</template>
					</div>
				</div>
			</div>

			<ion-modal
				:is-open="decisionOpen"
				@didDismiss="decisionOpen = false"
				:initial-breakpoint="1"
				:breakpoints="[0, 1]"
			>
				<div
					class="bg-ground w-full flex flex-col pb-8 max-h-[calc(100vh-5rem)]"
				>
					<div class="flex flex-col gap-1.5 px-4 pt-6 pb-5">
						<span class="g-eyebrow">{{ __("Remote check-in") }}</span>
						<span class="font-sans font-extrabold text-stat-number text-inkbase">
							{{
								decision === "approve" ? __("Approve this check-in?") : __("Reject this check-in?")
							}}
						</span>
						<span class="text-xs text-ink-600">
							{{ activeReq?.employee_name }} &middot; {{ activeReq?.log_type }} &middot;
							{{ formatTimestamp(activeReq?.checkin_time) }}
						</span>
					</div>

					<div class="flex flex-col gap-1.5 px-4 pt-1">
						<label class="text-xs text-ink-700">
							{{ __("Remarks (optional)") }}
						</label>
						<textarea
							v-model="decisionRemarks"
							rows="3"
							maxlength="500"
							class="w-full text-sm bg-surface border border-divider text-inkbase caret-accent p-2.5 resize-y outline-none focus:border-accent-ink"
						/>
					</div>

					<div class="flex flex-row gap-2.5 px-4 pt-4">
						<button
							class="flex-1 flex items-center justify-center bg-transparent border border-divider text-inkbase px-3.5 py-3 font-sans font-extrabold text-card-title hover:bg-ink-200 disabled:opacity-60"
							@click="decisionOpen = false"
							:disabled="submitting"
						>
							{{ __("Cancel") }}
						</button>
						<button
							class="flex-1 flex items-center justify-center gap-2 bg-accent-ink text-ground px-3.5 py-3 font-sans font-extrabold text-card-title hover:bg-accent-600 disabled:opacity-60"
							@click="submitDecision"
							:disabled="submitting"
						>
							<GSkeleton height="14px" width="42%" />
							{{ decision === "approve" ? __("Confirm Approve") : __("Confirm Reject") }}
						</button>
					</div>
				</div>
			</ion-modal>
		</ion-content>
	</GPage>
</template>

<script setup>
import GSkeleton from "@/components/glass/GSkeleton.vue"
import GPage from "@/components/glass/GPage.vue"
import { inject, onMounted, onBeforeUnmount, ref } from "vue"
import { useRoute, useRouter } from "vue-router"
import { IonContent, IonModal } from "@ionic/vue"
import { FeatherIcon, Button, toast } from "frappe-ui"
import GIconButton from "@/components/glass/GIconButton.vue"

import { formatTimestamp } from "@/utils/formatters"
import GSegmented from "@/components/glass/GSegmented.vue"
import {
	pendingForApproverResource,
	decidedForApproverResource,
	approveResource,
	rejectResource,
	pendingCountResource,
} from "@/data/remoteCheckin"

const __ = inject("$translate")
const socket = inject("$socket")
const router = useRouter()
const route = useRoute()

const pending = pendingForApproverResource
const decided = decidedForApproverResource
const TAB_BUTTONS = ["Pending", "History"] // __("Pending"), __("History")
// ?tab=History deep-links a decided request's notification straight to its
// History entry; anything else lands on the queue.
const activeTab = ref(route.query.tab === "History" ? "History" : "Pending")
const decisionOpen = ref(false)
const decision = ref("approve")
const decisionRemarks = ref("")
const activeReq = ref(null)
const submitting = ref(false)

const onRealtime = (event) => {
	console.info("[RemoteApprovals] realtime event:", event)
	pending.reload()
	decided.reload()
	if (event?.status === "Pending") {
		toast({
			title: __("New approval request"),
			text: event.subject || __("A team member submitted a remote check-in."),
			icon: "bell",
			position: "bottom-center",
			iconClasses: "text-accent-500",
		})
	}
}

onMounted(() => {
	pending.fetch()
	decided.fetch()
	socket?.on?.("hrms:remote_checkin_request", onRealtime)
})

onBeforeUnmount(() => {
	socket?.off?.("hrms:remote_checkin_request", onRealtime)
})

const reload = () => Promise.all([pending.reload(), decided.reload()])

const formatDistance = (d) => {
	const n = Number(d) || 0
	return n >= 1000 ? `${(n / 1000).toFixed(2)} km` : `${Math.round(n)} m`
}

const openDecision = (req, kind) => {
	activeReq.value = req
	decision.value = kind
	decisionRemarks.value = ""
	decisionOpen.value = true
}

const submitDecision = async () => {
	if (!activeReq.value) return
	submitting.value = true
	const resource = decision.value === "approve" ? approveResource : rejectResource
	try {
		await resource.submit({
			request: activeReq.value.name,
			approver_remarks: decisionRemarks.value.trim(),
		})
		toast({
			title: decision.value === "approve" ? __("Approved") : __("Rejected"),
			text: __("The employee has been notified."),
			icon: "check-circle",
			position: "bottom-center",
			iconClasses: "text-green-500",
		})
		decisionOpen.value = false
		// All three surfaces this decision changed. The realtime event cannot
		// cover them: the backend publishes the decision to the EMPLOYEE, not
		// to the deciding approver — without these the History tab misses the
		// row just decided and the Home/Profile badge keeps the old count.
		await Promise.all([pending.reload(), decided.reload(), pendingCountResource.reload()])
	} catch (err) {
		console.error("[RemoteApprovals] decision failed:", err)
		toast({
			title: __("Could not save"),
			text: err?.messages?.[0] || __("Try again."),
			icon: "alert-circle",
			position: "bottom-center",
			iconClasses: "text-red-500",
		})
	} finally {
		submitting.value = false
	}
}
</script>
