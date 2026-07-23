<template>
	<ion-modal
		:is-open="isOpen"
		@didDismiss="onDismiss"
		:initial-breakpoint="1"
		:breakpoints="[0, 1]"
	>
		<div class="bg-ground w-full flex flex-col pb-8 max-h-[calc(100vh-5rem)] border-t-[3px] border-inkbase">
			<div
				class="w-full flex flex-col gap-1 pt-6 pb-4 sticky top-0 z-[100] bg-ground px-4"
			>
				<div class="m-kicker">{{ __("Late check-out") }}</div>
				<span class="text-inkbase font-extrabold text-[22px] leading-tight">
					{{ __("Forgot to check out?") }}
				</span>
				<span class="text-xs text-ink-600">
					{{
						__(
							"Submit the time you actually left. Your reporting manager will review and approve."
						)
					}}
				</span>
			</div>

			<div class="w-full flex flex-col px-4 gap-3">
				<div class="bg-surface border border-divider px-3 py-2 text-xs text-inkbase">
					<div class="flex justify-between">
						<span class="text-ink-600">{{ __("Original check-in") }}</span>
						<span class="font-mono tabular-nums">{{ formatTimestamp(inCheckinTime) }}</span>
					</div>
				</div>

				<label class="text-xs uppercase text-ink-700 tracking-wide">
					{{ __("Actual Check-Out Time") }}
				</label>
				<input
					type="datetime-local"
					v-model="checkoutTime"
					:min="minCheckoutTime"
					:max="maxCheckoutTime"
					class="w-full text-sm bg-surface border border-divider p-2 text-inkbase focus:outline-none focus:border-accent"
				/>
				<div v-if="checkoutError" class="text-xs text-red-600">
					{{ checkoutError }}
				</div>

				<label class="text-xs uppercase text-ink-700 tracking-wide mt-2">
					{{ __("Why didn't you check out at the time?") }}
				</label>
				<textarea
					v-model="reason"
					rows="3"
					maxlength="500"
					class="w-full text-sm bg-surface border border-divider p-2 text-inkbase focus:outline-none focus:border-accent"
					:placeholder="
						__('e.g. left in a rush, low battery, network issue, etc.')
					"
				/>
				<div class="text-[10px] text-ink-500 text-right">
					{{ reason.length }}/500
				</div>
			</div>

			<div class="flex flex-row gap-2.5 px-4 pt-3">
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
					:disabled="submitting || !canSubmit"
				>
					{{ submitting ? __("Submitting…") : __("Submit") }}
				</button>
			</div>
		</div>
	</ion-modal>
</template>

<script setup>
import { computed, inject, ref, watch } from "vue"
import { IonModal } from "@ionic/vue"
import { toast } from "frappe-ui"

import { formatTimestamp } from "@/utils/formatters"
import { submitLateCheckoutResource } from "@/data/remoteCheckin"

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
	return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`
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
	() =>
		!!checkoutTime.value &&
		!!reason.value.trim() &&
		!checkoutError.value
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

const submit = async () => {
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
		toast({
			title: __("Late check-out submitted"),
			text: __("Pending approval from your reporting manager."),
			icon: "check-circle",
			position: "bottom-center",
			iconClasses: "text-green-500",
		})
		emit("submitted", result)
		emit("close")
	} catch (err) {
		console.error("[LateCheckout] submit failed:", err)
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

const cancel = () => emit("close")
const onDismiss = () => emit("close")
</script>
