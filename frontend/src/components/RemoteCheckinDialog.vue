<template>
	<GModal :is-open="isOpen" @did-dismiss="onDismiss">
		<div class="bg-bg w-full flex flex-col pb-8 max-h-sheet">
			<div class="w-full flex flex-col gap-1 pt-6 pb-4 sticky top-0 z-overlay bg-bg px-4">
				<div class="g-eyebrow">{{ __("Remote check-in") }}</div>
				<span class="text-ink font-extrabold text-stat-number leading-tight">
					{{ headline }}
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
				<!-- An unplaceable reading computes to a distance of 0 m, so the
				     metric row is hidden rather than shown as a reassuring lie.
				     A COARSE one is hidden for the same reason: since 17 Sep 2026
				     a reading of a few hundred metres' error is placed rather
				     than refused, so a far one arrives as `outside_radius` and
				     would otherwise show a confident figure drawn from a reading
				     that cannot support it. -->
				<div
					v-if="reason !== 'imprecise_location' && !readingIsCoarse"
					class="bg-brand/15 border border-brand px-3 py-2 text-xs text-accent-ink"
				>
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
					class="w-full text-sm bg-track-solid border border-hair p-2 text-ink focus:outline-none focus:border-brand"
					:placeholder="__('e.g. Client meeting at office X, traffic to KLCC, etc.')"
				/>
				<div class="text-caption text-ink-500 text-right">{{ remarks.length }}/500</div>
			</div>

			<div class="flex flex-row gap-2.5 px-4 pt-2">
				<button
					class="flex-1 bg-transparent border border-hair text-ink px-3.5 py-3 font-sans font-extrabold text-card-title cursor-pointer text-left hover:bg-ink/[0.07] disabled:opacity-60"
					@click="cancel"
					:disabled="submitting"
				>
					{{ __("Cancel") }}
				</button>
				<button
					class="flex-1 bg-brand text-on-brand border-none px-3.5 py-3 font-sans font-extrabold text-card-title cursor-pointer text-left hover:bg-brand disabled:opacity-60"
					@click="submit"
					:disabled="submitting || !remarks.trim()"
				>
					{{ submitting ? __("Submitting…") : __("Submit Request") }}
				</button>
			</div>
		</div>
	</GModal>
</template>

<script setup>
import { ACCURACY_ALLOWANCE_CAP_M } from "@/utils/geolocation"
import GModal from "@/components/glass/GModal.vue"
import { computed, inject, ref, watch } from "vue"
import { toast } from "frappe-ui"

import { submitRemarksResource } from "@/data/remoteCheckin"
import { firstMessage } from "@/utils/loudRequest"

const __ = inject("$translate")

const props = defineProps({
	isOpen: { type: Boolean, default: false },
	requestName: { type: String, default: "" },
	logType: { type: String, default: "IN" },
	distanceM: { type: Number, default: 0 },
	// How wide the device said its own error was, in metres. 0 means unknown.
	accuracyM: { type: Number, default: 0 },
	approverName: { type: String, default: "" },
	reason: {
		type: String,
		default: "outside_radius",
		// "outside_radius" | "imprecise_location"
	},
})

const emit = defineEmits(["close", "submitted"])

const remarks = ref("")
const submitting = ref(false)

// Two different things send a punch to an approver, and telling someone they
// left the geofence when their phone simply could not see the sky is both
// wrong and the kind of wrong that gets argued about at payroll.
const headline = computed(() =>
	props.reason === "imprecise_location"
		? __("We couldn't confirm where you are")
		: __("You're outside the office geofence")
)

// Past the allowance cap the reading cannot widen a fence, so its distance is
// not a figure to put in front of anybody. The reason code used to stand in for
// this and no longer does.
const readingIsCoarse = computed(() => Number(props.accuracyM) > ACCURACY_ALLOWANCE_CAP_M)

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
			iconClasses: "text-danger-ink",
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
			iconClasses: "text-success-ink",
		})
		emit("submitted", { request: props.requestName, remarks: remarks.value })
		emit("close")
	} catch (err) {
		console.error("[RemoteCheckin] submit failed:", err)
		toast({
			title: __("Could not submit"),
			text: firstMessage(err, __("Try again in a moment.")),
			icon: "alert-circle",
			position: "bottom-center",
			iconClasses: "text-danger-ink",
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
