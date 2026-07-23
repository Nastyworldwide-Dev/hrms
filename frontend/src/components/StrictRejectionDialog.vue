<template>
	<ion-modal
		:is-open="isOpen"
		@didDismiss="onDismiss"
		:initial-breakpoint="1"
		:breakpoints="[0, 1]"
	>
		<div class="bg-ground w-full flex flex-col pb-5 max-h-[calc(100vh-5rem)] border-t-[3px] border-inkbase">
			<div
				class="w-full flex flex-col gap-2 pt-6 pb-4 px-4 border-b border-divider sticky top-0 z-[100] bg-ground"
			>
				<div
					class="h-12 w-12 bg-red-100 flex items-center justify-center"
				>
					<FeatherIcon name="slash" class="h-6 w-6 text-red-600" />
				</div>
				<div class="m-kicker">{{ __("Check-in") }}</div>
				<span class="text-inkbase font-extrabold text-[22px] leading-tight">
					{{ title }}
				</span>
				<span class="text-xs text-ink-600">
					{{ subtitle }}
				</span>
			</div>

			<div class="w-full flex flex-col px-4 pt-4 gap-3">
				<!-- outside_radius: distance card + location summary -->
				<template v-if="reason === 'outside_radius'">
					<div class="bg-red-50 border border-red-200 px-3 py-2.5">
						<div class="flex justify-between text-xs text-red-800">
							<span>{{ __("Distance from geofence") }}</span>
							<span class="font-mono font-semibold">
								{{ formattedOvershoot }}
							</span>
						</div>
						<div class="flex justify-between text-xs text-red-700 mt-1">
							<span>{{ __("Allowed radius") }}</span>
							<span class="font-mono">{{ radiusM }} m</span>
						</div>
					</div>

					<div class="bg-surface border border-divider px-3 py-2.5">
						<div class="m-kicker">
							{{ __("Shift Location") }}
						</div>
						<div class="text-sm font-medium text-inkbase mt-0.5">
							{{ shiftLocation || __("(unnamed)") }}
						</div>
						<div class="m-kicker mt-2">
							{{ __("Shift") }}
						</div>
						<div class="text-sm font-medium text-inkbase mt-0.5">
							{{ shiftType || __("(unknown)") }}
						</div>
					</div>
				</template>

				<!-- no_shift_location / no_radius: admin misconfiguration -->
				<template v-else>
					<div class="bg-red-50 border border-red-200 px-3 py-3">
						<div class="flex items-start gap-2">
							<FeatherIcon
								name="alert-triangle"
								class="h-4 w-4 text-red-600 mt-0.5 shrink-0"
							/>
							<div class="text-xs text-red-800 leading-relaxed">
								{{ adminMisconfigMessage }}
							</div>
						</div>
					</div>
				</template>
			</div>

			<div class="flex flex-col gap-2 px-4 pt-4">
				<Button class="w-full py-5 !bg-accent hover:!bg-accent-600 !text-ground !border-none" variant="solid" @click="close">
					{{ __("OK") }}
				</Button>
				<button
					class="w-full text-xs text-ink-600 underline py-2"
					@click="contactHR"
				>
					{{ __("Contact HR") }}
				</button>
			</div>
		</div>
	</ion-modal>
</template>

<script setup>
import { computed, inject } from "vue"
import { IonModal } from "@ionic/vue"
import { FeatherIcon, Button } from "frappe-ui"

const __ = inject("$translate")

const props = defineProps({
	isOpen: { type: Boolean, default: false },
	reason: {
		type: String,
		default: "outside_radius",
		// "outside_radius" | "no_shift_location" | "no_radius"
	},
	shiftType: { type: String, default: "" },
	shiftLocation: { type: String, default: "" },
	distanceM: { type: Number, default: 0 },
	radiusM: { type: Number, default: 0 },
	overshootM: { type: Number, default: 0 },
})

const emit = defineEmits(["close"])

const title = computed(() => {
	switch (props.reason) {
		case "no_shift_location":
			return __("Check-in unavailable")
		case "no_radius":
			return __("Check-in unavailable")
		default:
			return __("Check-in blocked")
	}
})

const subtitle = computed(() => {
	switch (props.reason) {
		case "no_shift_location":
		case "no_radius":
			return __("Your shift is configured for strict geofencing but isn't ready yet.")
		default:
			return __(
				"You are outside the shift location radius. Remote approval is not available for this shift."
			)
	}
})

const adminMisconfigMessage = computed(() => {
	if (props.reason === "no_shift_location") {
		return __(
			"Strict geofencing is enabled for shift {0}, but no Shift Location is set on your Shift Assignment. Ask your HR administrator to assign one.",
			[props.shiftType || __("(unknown)")]
		)
	}
	// no_radius
	return __(
		"Shift Location {0} has no check-in radius configured. Ask your HR administrator to set one.",
		[props.shiftLocation || __("(unnamed)")]
	)
})

const formattedOvershoot = computed(() => {
	const m = Math.round(props.overshootM || 0)
	if (m >= 1000) return `+${(m / 1000).toFixed(2)} km over`
	return `+${m} m over`
})

function close() {
	emit("close")
}

function onDismiss() {
	emit("close")
}

function contactHR() {
	// Stub — wire to the existing HR Contacts view if available, otherwise
	// a simple mailto could be slotted in by the host page.
	console.info("[StrictRejection] Contact HR tapped")
	emit("close")
}
</script>
