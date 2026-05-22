<template>
	<ion-modal
		:is-open="isOpen"
		@didDismiss="onDismiss"
		:initial-breakpoint="1"
		:breakpoints="[0, 1]"
	>
		<div class="bg-white w-full flex flex-col pb-5 max-h-[calc(100vh-5rem)]">
			<div
				class="w-full flex flex-col gap-2 pt-8 pb-5 border-b items-center sticky top-0 z-[100] bg-white"
			>
				<div
					class="h-12 w-12 rounded-full bg-amber-100 flex items-center justify-center"
				>
					<FeatherIcon name="map-pin" class="h-6 w-6 text-amber-700" />
				</div>
				<span class="text-gray-900 font-bold text-base">
					{{ __("You're outside the office geofence") }}
				</span>
				<span class="text-xs text-gray-500 px-6 text-center">
					{{
						__(
							"Submit a remote {0} request. Your reporting manager will be notified for approval.",
							[logType === "IN" ? __("check-in") : __("check-out")]
						)
					}}
				</span>
			</div>

			<div class="w-full flex flex-col px-4 pt-4 gap-3">
				<div class="bg-amber-50 border border-amber-200 rounded-md px-3 py-2 text-xs text-amber-800">
					<div class="flex justify-between">
						<span>{{ __("Distance from geofence") }}</span>
						<span class="font-mono font-semibold">{{ formattedDistance }}</span>
					</div>
				</div>

				<label class="text-xs uppercase text-gray-500 tracking-wide">
					{{ __("Reason for remote {0}", [logType === "IN" ? "check-in" : "check-out"]) }}
				</label>
				<textarea
					v-model="remarks"
					rows="4"
					maxlength="500"
					class="w-full text-sm border border-gray-300 rounded-md p-2 focus:outline-none focus:ring-1 focus:ring-blue-500"
					:placeholder="
						__('e.g. Client meeting at office X, traffic to KLCC, etc.')
					"
				/>
				<div class="text-[10px] text-gray-400 text-right">
					{{ remarks.length }}/500
				</div>
			</div>

			<div class="flex flex-row gap-2 px-4 pt-2">
				<Button
					variant="outline"
					class="flex-1"
					@click="cancel"
					:disabled="submitting"
				>
					{{ __("Cancel") }}
				</Button>
				<Button
					class="flex-1"
					theme="blue"
					@click="submit"
					:loading="submitting"
					:disabled="!remarks.trim()"
				>
					{{ __("Submit Request") }}
				</Button>
			</div>
		</div>
	</ion-modal>
</template>

<script setup>
import { computed, inject, ref, watch } from "vue"
import { IonModal } from "@ionic/vue"
import { FeatherIcon, Button, toast } from "frappe-ui"

import { submitRemarksResource } from "@/data/remoteCheckin"

const __ = inject("$translate")

const props = defineProps({
	isOpen: { type: Boolean, default: false },
	requestName: { type: String, default: "" },
	logType: { type: String, default: "IN" },
	distanceM: { type: Number, default: 0 },
	approverName: { type: String, default: "" },
})

const emit = defineEmits(["close", "submitted"])

const remarks = ref("")
const submitting = ref(false)

const formattedDistance = computed(() => {
	const d = props.distanceM || 0
	return d >= 1000 ? `${(d / 1000).toFixed(2)} km` : `${Math.round(d)} m`
})

watch(
	() => props.isOpen,
	(open) => {
		if (open) {
			remarks.value = ""
			submitting.value = false
		}
	}
)

const submit = async () => {
	if (!props.requestName) {
		toast({
			title: __("Error"),
			text: __("Request reference missing — try checking in again."),
			icon: "alert-circle",
			position: "bottom-center",
			iconClasses: "text-red-500",
		})
		return
	}
	submitting.value = true
	try {
		await submitRemarksResource.submit({
			request: props.requestName,
			employee_remarks: remarks.value.trim(),
		})
		toast({
			title: __("Request submitted"),
			text: props.approverName
				? __("Pending approval from {0}", [props.approverName])
				: __("Pending approval from your reporting manager"),
			icon: "check-circle",
			position: "bottom-center",
			iconClasses: "text-green-500",
		})
		emit("submitted", { request: props.requestName, remarks: remarks.value })
		emit("close")
	} catch (err) {
		console.error("[RemoteCheckin] submit failed:", err)
		toast({
			title: __("Could not submit"),
			text: err?.messages?.[0] || __("Try again in a moment."),
			icon: "alert-circle",
			position: "bottom-center",
			iconClasses: "text-red-500",
		})
	} finally {
		submitting.value = false
	}
}

const cancel = () => {
	emit("close")
}

const onDismiss = () => {
	emit("close")
}
</script>
