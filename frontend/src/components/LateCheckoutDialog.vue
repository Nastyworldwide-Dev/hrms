<template>
	<!-- On the kit (owner, 25 Sep 2026: old hand-drawn sheets): the check-in is
	     a row, the time and the reason are the kit's fields, the count is the
	     footer, Cancel / Send are the kit's two buttons. -->
	<GModal :is-open="isOpen" :title="__('Forgot to check out?')" @did-dismiss="onDismiss">
		<div class="g-form-body">
			<section class="g-form-section">
				<div class="g-form-group">
					<div class="g-form-row g-form-row--readonly">
						<span class="g-form-row__label">{{ __("You checked in") }}</span>
						<span class="g-form-row__value tabular-nums">{{ formatTimestamp(inCheckinTime) }}</span>
					</div>
				</div>
				<p class="g-form-footer">
					{{ __("Send the time you actually left. Your approver is asked to approve it.") }}
				</p>
			</section>

			<section class="g-form-section">
				<div class="g-form-group">
					<label class="g-form-row">
						<span class="g-form-row__label">{{ __("Time you left") }}</span>
						<GInput
							v-model="checkoutTime"
							type="datetime-local"
							:aria-label="__('Time you left')"
							:min="minCheckoutTime"
							:max="maxCheckoutTime"
							:error="checkoutError || ''"
						/>
					</label>
					<div class="g-form-row g-form-row--stacked">
						<span class="g-form-row__label">{{ __("Why didn't you check out then?") }}</span>
						<GTextarea
							v-model="reason"
							:aria-label="__('Why didn\'t you check out then?')"
							:placeholder="__('e.g. left in a rush, low battery, no signal')"
							:maxlength="500"
						/>
					</div>
				</div>
				<p class="g-form-footer">{{ __("{0} of 500", [reason.length]) }}</p>
			</section>

			<div class="flex flex-row gap-3">
				<GGhostButton class="flex-1" :label="__('Cancel')" :disabled="submitting" @click="cancel" />
				<GButton
					class="flex-1"
					:label="__('Send')"
					:pending="submitting"
					:disabled="submitting || !canSubmit || !online"
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
import GModal from "@/components/glass/GModal.vue"
import GButton from "@/components/glass/GButton.vue"
import GGhostButton from "@/components/glass/GGhostButton.vue"
import GInput from "@/components/glass/GInput.vue"
import GTextarea from "@/components/glass/GTextarea.vue"
import { useOnline } from "@/composables/useOnline"
import { computed, inject, ref, watch } from "vue"
import { gToast } from "@/components/glass/toast"

import { formatTimestamp } from "@/utils/formatters"
import { submitLateCheckoutResource } from "@/data/remoteCheckin"
import { firstMessage } from "@/utils/loudRequest"

const __ = inject("$translate")

const props = defineProps({
	isOpen: { type: Boolean, default: false },
	inCheckinName: { type: String, default: "" },
	inCheckinTime: { type: String, default: "" },
})

const emit = defineEmits(["close", "submitted"])

const checkoutTime = ref("")
const reason = ref("")
const submitting = ref(false)

const toInputValue = (date) => {
	// Convert Date or ISO string to "YYYY-MM-DDTHH:mm" for datetime-local input
	const d = typeof date === "string" ? new Date(date.replace(" ", "T")) : date
	const pad = (n) => String(n).padStart(2, "0")
	return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(
		d.getHours()
	)}:${pad(d.getMinutes())}`
}

const minCheckoutTime = computed(() => {
	if (!props.inCheckinTime) return ""
	const t = new Date(props.inCheckinTime.replace(" ", "T"))
	// allow 1 minute after the IN as the floor
	return toInputValue(new Date(t.getTime() + 60000))
})

const maxCheckoutTime = computed(() => toInputValue(new Date()))

const checkoutError = computed(() => {
	if (!checkoutTime.value) return ""
	const out = new Date(checkoutTime.value)
	if (Number.isNaN(out.getTime())) return __("Invalid date/time.")
	if (props.inCheckinTime) {
		const inT = new Date(props.inCheckinTime.replace(" ", "T"))
		if (out <= inT) return __("Must be after the check-in time.")
	}
	if (out > new Date()) return __("Cannot be in the future.")
	return ""
})

const canSubmit = computed(
	() => !!checkoutTime.value && !!reason.value.trim() && !checkoutError.value
)

watch(
	() => props.isOpen,
	(open) => {
		if (open) {
			reason.value = ""
			submitting.value = false
			// Default to "end of the day the IN happened" — gives the user a useful start.
			if (props.inCheckinTime) {
				const inT = new Date(props.inCheckinTime.replace(" ", "T"))
				const def = new Date(inT)
				def.setHours(18, 0, 0, 0)
				const now = new Date()
				checkoutTime.value = toInputValue(def < now ? def : now)
			} else {
				checkoutTime.value = ""
			}
		}
	}
)

//: Owner ruling (22 Sep): never an offline check-in. This dialog sends a punch,
//: so it is blocked offline like the panel that opens it (audit P0-7).
const online = useOnline()

const submit = async () => {
	if (!online.value) {
		console.warn("[LateCheckoutDialog] refused a submit while offline")
		return
	}
	if (!canSubmit.value) return
	submitting.value = true
	try {
		// Backend expects "YYYY-MM-DD HH:mm:ss"
		const isoLocal = checkoutTime.value.replace("T", " ") + ":00"
		const result = await submitLateCheckoutResource.submit({
			in_checkin: props.inCheckinName,
			checkout_datetime: isoLocal,
			reason: reason.value.trim(),
		})
		gToast({
			title: __("Late check-out submitted"),
			text: __("Pending approval from your reporting manager."),
			variant: "success",
		})
		emit("submitted", result)
		emit("close")
	} catch (err) {
		console.error("[LateCheckout] submit failed:", err)
		gToast({
			title: __("Could not submit"),
			text: firstMessage(err, __("Try again in a moment.")),
			variant: "error",
		})
	} finally {
		submitting.value = false
	}
}

const cancel = () => emit("close")
const onDismiss = () => emit("close")
</script>
