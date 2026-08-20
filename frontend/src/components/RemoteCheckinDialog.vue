<template>
	<ion-modal
		:is-open="isOpen"
		@didDismiss="onDismiss"
		:initial-breakpoint="1"
		:breakpoints="[0, 1]"
	>
		<div class="bg-ground w-full flex flex-col pb-8 max-h-sheet border-t-[3px] border-inkbase">
			<div
				class="w-full flex flex-col gap-1 pt-6 pb-4 sticky top-0 z-overlay bg-ground px-4"
			>
				<div class="m-kicker">{{ __("Remote check-in") }}</div>
				<span class="text-inkbase font-extrabold text-[22px] leading-tight">
					{{ __("You're outside the office geofence") }}
				</span>
				<span class="text-xs text-ink-600">
					{{
						__(
							"Submit a remote {0} request. Your reporting manager will be notified for approval.",
							[logType === "IN" ? __("check-in") : __("check-out")]
						)
					}}
				</span>
			</div>

			<div class="w-full flex flex-col px-4 gap-3">
				<div class="bg-accent-100 border border-accent px-3 py-2 text-xs text-accent-800">
					<div class="flex justify-between">
						<span>{{ __("Distance from geofence") }}</span>
						<span class="font-mono font-semibold tabular-nums">{{ formattedDistance }}</span>
					</div>
				</div>

				<label class="text-xs uppercase text-ink-700 tracking-wide">
					{{ __("Reason for remote {0}", [logType === "IN" ? "check-in" : "check-out"]) }}
				</label>
				<textarea
					v-model="remarks"
					rows="4"
					maxlength="500"
					class="w-full text-sm bg-surface border border-divider p-2 text-inkbase focus:outline-none focus:border-accent"
					:placeholder="
						__('e.g. Client meeting at office X, traffic to KLCC, etc.')
					"
				/>
				<div class="text-[10px] text-ink-500 text-right">
					{{ remarks.length }}/500
				</div>
			</div>

			<div class="flex flex-row gap-2.5 px-4 pt-2">
				<button
					class="flex-1 bg-transparent border border-divider text-inkbase px-3.5 py-3 font-sans font-extrabold text-[13px] cursor-pointer text-left hover:bg-inkbase/[0.07] disabled:opacity-60"
					@click="cancel"
					:disabled="submitting"
				>
					{{ __("Cancel") }}
				</button>
				<button
					class="flex-1 bg-accent text-ground border-none px-3.5 py-3 font-sans font-extrabold text-[13px] cursor-pointer text-left hover:bg-accent-600 disabled:opacity-60"
					@click="submit"
					:disabled="submitting || !remarks.trim()"
				>
					{{ submitting ? __("Submitting…") : __("Submit Request") }}
				</button>
			</div>
		</div>
	</ion-modal>
</template>

<script setup>
import { computed, inject, ref, watch } from "vue"
import { IonModal } from "@ionic/vue"
import { toast } from "frappe-ui"

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
