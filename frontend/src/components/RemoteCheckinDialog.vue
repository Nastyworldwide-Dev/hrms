<template>
	<!-- On the kit (owner, 25 Sep 2026: "another old frappe design"): the
	     facts are rows in one group, the reason is the kit's text area with its
	     count as the footer, and Cancel / Send are the kit's two buttons. It was
	     square hand-drawn buttons, a lime box, and a raw textarea. -->
	<GModal :is-open="isOpen" :title="headline" @did-dismiss="onDismiss">
		<div class="g-form-body">
			<section class="g-form-section">
				<!-- An unplaceable reading computes to a distance of 0 m, so the
				     row is hidden rather than shown as a reassuring lie. A COARSE
				     one is hidden for the same reason: since 17 Sep 2026 a reading
				     of a few hundred metres' error is placed rather than refused,
				     so a far one arrives as `outside_radius` and would otherwise
				     show a confident figure drawn from a reading that cannot
				     support it. -->
				<div v-if="reason !== 'imprecise_location' && !readingIsCoarse" class="g-form-group">
					<div class="g-form-row g-form-row--readonly">
						<span class="g-form-row__label">{{ __("From the work area") }}</span>
						<span class="g-form-row__value tabular-nums">{{ formattedDistance }}</span>
					</div>
				</div>
				<p class="g-form-footer">
					{{
						__("Your approver is asked to approve this {0}.", [
							logType === "IN" ? __("check-in") : __("check-out"),
						])
					}}
				</p>
			</section>

			<section class="g-form-section">
				<div class="g-form-group">
					<!-- A stacked row: its label on top, the text under it, as every
					     long-text field in a group (FormField). -->
					<div class="g-form-row g-form-row--stacked">
						<span class="g-form-row__label">{{ __("Why are you away from the work area?") }}</span>
						<GTextarea
							v-model="remarks"
							:aria-label="__('Why are you away from the work area?')"
							:placeholder="__('e.g. meeting a client, working from home as asked')"
							:maxlength="500"
						/>
					</div>
				</div>
				<p class="g-form-footer">{{ __("{0} of 500", [remarks.length]) }}</p>
			</section>

			<div class="flex flex-row gap-3">
				<GGhostButton class="flex-1" :label="__('Cancel')" :disabled="submitting" @click="cancel" />
				<GButton
					class="flex-1"
					:label="__('Send request')"
					:pending="submitting"
					:disabled="submitting || !remarks.trim() || !online"
					@click="submit"
				/>
			</div>
			<!-- Owner ruling: never an offline check-in (audit P0-7). -->
			<p v-if="!online" class="g-form-footer" role="status">
				{{ __("You need signal to check in.") }}
			</p>
		</div>
	</GModal>
</template>

<script setup>
import { isReadingCoarse } from "@/utils/geolocation"
import GModal from "@/components/glass/GModal.vue"
import GButton from "@/components/glass/GButton.vue"
import GGhostButton from "@/components/glass/GGhostButton.vue"
import GTextarea from "@/components/glass/GTextarea.vue"
import { useOnline } from "@/composables/useOnline"
import { computed, inject, ref, watch } from "vue"
import { gToast } from "@/components/glass/toast"

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

// Past the allowance cap the reading cannot widen a fence, so its distance is
// not a figure to put in front of anybody. The reason code used to stand in for
// this and no longer does.
const readingIsCoarse = computed(() => isReadingCoarse(props.accuracyM))

// Two different things send a punch to an approver, and telling someone they
// left the geofence when their phone simply could not see the sky is both
// wrong and the kind of wrong that gets argued about at payroll.
const headline = computed(() =>
	// The headline must not assert what the metric row beside it has just
	// refused to show. A coarse reading is "we could not confirm", whatever
	// verdict it produced.
	props.reason === "imprecise_location" || readingIsCoarse.value
		? __("We couldn't confirm where you are")
		: __("You're outside the office geofence")
)

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

//: Owner ruling (22 Sep): never an offline check-in. This dialog sends a punch,
//: so it is blocked offline like the panel that opens it (audit P0-7).
const online = useOnline()

const submit = async () => {
	if (!online.value) {
		console.warn("[RemoteCheckinDialog] refused a submit while offline")
		return
	}
	if (!props.requestName) {
		gToast({
			title: __("Error"),
			text: __("Request reference missing — try checking in again."),
			variant: "error",
		})
		return
	}
	submitting.value = true
	try {
		await submitRemarksResource.submit({
			request: props.requestName,
			employee_remarks: remarks.value.trim(),
		})
		gToast({
			title: __("Request submitted"),
			text: props.approverName
				? __("Pending approval from {0}", [props.approverName])
				: __("Pending approval from your reporting manager"),
			variant: "success",
		})
		emit("submitted", { request: props.requestName, remarks: remarks.value })
		emit("close")
	} catch (err) {
		console.error("[RemoteCheckin] submit failed:", err)
		gToast({
			title: __("Could not submit"),
			text: firstMessage(err, __("Try again in a moment.")),
			variant: "error",
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
