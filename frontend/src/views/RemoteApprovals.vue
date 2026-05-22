<template>
	<ion-page>
		<ion-content class="ion-padding">
			<div class="flex flex-col h-screen w-screen">
				<div class="w-full sm:w-96">
					<header
						class="flex flex-row bg-white shadow-sm py-4 px-3 items-center justify-between border-b sticky top-0 z-10"
					>
						<div class="flex flex-row items-center">
							<Button
								variant="ghost"
								class="!pl-0 hover:bg-white"
								@click="router.back()"
							>
								<FeatherIcon name="chevron-left" class="h-5 w-5" />
							</Button>
							<h2 class="text-xl font-semibold text-gray-900">
								{{ __("Pending Approvals") }}
							</h2>
						</div>
						<Button
							variant="ghost"
							class="hover:bg-white"
							@click="reload"
							:loading="pending.loading"
						>
							<FeatherIcon name="refresh-cw" class="h-4 w-4" />
						</Button>
					</header>

					<div class="flex flex-col mt-3 p-3 gap-3">
						<div v-if="pending.loading && !pending.data" class="space-y-3">
							<div
								v-for="i in 3"
								:key="i"
								class="h-28 bg-gray-100 animate-pulse rounded-md"
							/>
						</div>

						<div
							v-else-if="!pending.data || pending.data.length === 0"
							class="flex flex-col items-center justify-center py-16 px-6 text-center"
						>
							<div
								class="h-16 w-16 rounded-full bg-gray-100 flex items-center justify-center mb-3"
							>
								<FeatherIcon name="check-circle" class="h-7 w-7 text-gray-400" />
							</div>
							<div class="text-sm font-medium text-gray-700">
								{{ __("Nothing to approve right now") }}
							</div>
							<div class="text-xs text-gray-500 mt-1">
								{{ __("Remote check-ins from your team will show up here.") }}
							</div>
						</div>

						<div
							v-else
							v-for="req in pending.data"
							:key="req.name"
							class="bg-white rounded-md border border-gray-200 p-3 flex flex-col gap-2"
						>
							<div class="flex flex-row items-center justify-between">
								<div class="text-sm font-semibold text-gray-900 truncate">
									{{ req.employee_name || req.employee }}
								</div>
								<span
									class="text-[10px] font-semibold px-2 py-0.5 rounded uppercase"
									:class="
										req.log_type === 'IN'
											? 'bg-emerald-100 text-emerald-700'
											: 'bg-orange-100 text-orange-700'
									"
								>
									{{ req.log_type }}
								</span>
							</div>
							<div class="flex flex-row items-center justify-between text-xs text-gray-500">
								<span>{{ formatTimestamp(req.checkin_time) }}</span>
								<span class="font-mono">{{ formatDistance(req.distance_m) }}</span>
							</div>
							<div
								v-if="req.employee_remarks"
								class="text-xs text-gray-700 bg-gray-50 border border-gray-100 rounded p-2"
							>
								{{ req.employee_remarks }}
							</div>
							<div
								v-else
								class="text-xs text-gray-400 italic"
							>
								{{ __("No reason provided.") }}
							</div>
							<div class="flex flex-row gap-2 mt-1">
								<Button
									variant="outline"
									class="flex-1"
									theme="red"
									@click="openDecision(req, 'reject')"
								>
									{{ __("Reject") }}
								</Button>
								<Button
									class="flex-1"
									theme="green"
									@click="openDecision(req, 'approve')"
								>
									{{ __("Approve") }}
								</Button>
							</div>
						</div>
					</div>
				</div>
			</div>

			<ion-modal
				:is-open="decisionOpen"
				@didDismiss="decisionOpen = false"
				:initial-breakpoint="1"
				:breakpoints="[0, 1]"
			>
				<div class="bg-white w-full flex flex-col pb-5 max-h-[calc(100vh-5rem)]">
					<div class="flex flex-col gap-1 pt-8 pb-5 border-b items-center">
						<span class="text-gray-900 font-bold text-base">
							{{
								decision === "approve"
									? __("Approve this check-in?")
									: __("Reject this check-in?")
							}}
						</span>
						<span class="text-xs text-gray-500">
							{{ activeReq?.employee_name }} &middot; {{ activeReq?.log_type }} &middot;
							{{ formatTimestamp(activeReq?.checkin_time) }}
						</span>
					</div>

					<div class="flex flex-col gap-2 px-4 pt-4">
						<label class="text-xs uppercase text-gray-500 tracking-wide">
							{{ __("Remarks (optional)") }}
						</label>
						<textarea
							v-model="decisionRemarks"
							rows="3"
							maxlength="500"
							class="w-full text-sm border border-gray-300 rounded-md p-2 focus:outline-none focus:ring-1 focus:ring-blue-500"
						/>
					</div>

					<div class="flex flex-row gap-2 px-4 pt-3">
						<Button
							variant="outline"
							class="flex-1"
							@click="decisionOpen = false"
							:disabled="submitting"
						>
							{{ __("Cancel") }}
						</Button>
						<Button
							class="flex-1"
							:theme="decision === 'approve' ? 'green' : 'red'"
							@click="submitDecision"
							:loading="submitting"
						>
							{{
								decision === "approve"
									? __("Confirm Approve")
									: __("Confirm Reject")
							}}
						</Button>
					</div>
				</div>
			</ion-modal>
		</ion-content>
	</ion-page>
</template>

<script setup>
import { inject, onMounted, ref } from "vue"
import { useRouter } from "vue-router"
import { IonPage, IonContent, IonModal } from "@ionic/vue"
import { FeatherIcon, Button, toast } from "frappe-ui"

import { formatTimestamp } from "@/utils/formatters"
import {
	pendingForApproverResource,
	approveResource,
	rejectResource,
} from "@/data/remoteCheckin"

const __ = inject("$translate")
const router = useRouter()

const pending = pendingForApproverResource
const decisionOpen = ref(false)
const decision = ref("approve")
const decisionRemarks = ref("")
const activeReq = ref(null)
const submitting = ref(false)

onMounted(() => {
	pending.fetch()
})

const reload = () => pending.reload()

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
			title:
				decision.value === "approve"
					? __("Approved")
					: __("Rejected"),
			text: __("The employee has been notified."),
			icon: "check-circle",
			position: "bottom-center",
			iconClasses: "text-green-500",
		})
		decisionOpen.value = false
		await pending.reload()
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
