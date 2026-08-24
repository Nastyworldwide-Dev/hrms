<template>
	<GModal :is-open="isOpen" @did-dismiss="onDismiss">
		<div class="bg-bg w-full flex flex-col pb-5 max-h-sheet">
			<div
				class="w-full flex flex-col gap-2 pt-6 pb-4 px-4 border-b border-hair sticky top-0 z-overlay bg-bg"
			>
				<div
					class="h-12 w-12 bg-danger/15 flex items-center justify-center"
				>
					<FeatherIcon name="slash" class="h-6 w-6 text-danger-ink" />
				</div>
				<div class="g-eyebrow">{{ __("Check-in") }}</div>
				<span class="text-ink font-extrabold text-stat-number leading-tight">
					{{ title }}
				</span>
				<span class="text-xs text-ink-600">
					{{ subtitle }}
				</span>
			</div>

			<div class="w-full flex flex-col px-4 pt-4 gap-3">
				<!-- outside_radius: distance card + location summary -->
				<template v-if="reason === 'outside_radius'">
					<div class="bg-danger/10 border border-danger-ink px-3 py-2.5">
						<div class="flex justify-between text-xs text-danger-ink">
							<span>{{ __("Distance from geofence") }}</span>
							<span class="font-mono font-semibold">
								{{ formattedOvershoot }}
							</span>
						</div>
						<div class="flex justify-between text-xs text-danger-ink mt-1">
							<span>{{ __("Allowed radius") }}</span>
							<span class="font-mono">{{ radiusM }} m</span>
						</div>
					</div>

					<div class="bg-track-solid border border-hair px-3 py-2.5">
						<div class="g-eyebrow">
							{{ __("Shift Location") }}
						</div>
						<div class="text-sm font-medium text-ink mt-0.5">
							{{ shiftLocation || __("(unnamed)") }}
						</div>
						<div class="g-eyebrow mt-2">
							{{ __("Shift") }}
						</div>
						<div class="text-sm font-medium text-ink mt-0.5">
							{{ shiftType || __("(unknown)") }}
						</div>
					</div>
				</template>

				<!-- imprecise_location: the reading, not the employee, is the problem -->
				<template v-else-if="reason === 'imprecise_location'">
					<div class="bg-danger/10 border border-danger-ink px-3 py-2.5">
						<div class="flex justify-between text-xs text-danger-ink">
							<span>{{ __("Your device's accuracy") }}</span>
							<span class="font-mono font-semibold">
								{{ formattedAccuracy }}
							</span>
						</div>
						<div class="flex justify-between text-xs text-danger-ink mt-1">
							<span>{{ __("Allowed radius") }}</span>
							<span class="font-mono">{{ radiusM }} m</span>
						</div>
					</div>

					<div class="bg-track-solid border border-hair px-3 py-2.5">
						<div class="text-xs text-ink-600 leading-relaxed">
							{{
								__(
									"A phone indoors or a computer without GPS can only guess its position. Move near a window, turn wifi on, or check in from your phone."
								)
							}}
						</div>
					</div>
				</template>

				<!-- no_shift_location / no_radius: admin misconfiguration -->
				<template v-else>
					<div class="bg-danger/10 border border-danger-ink px-3 py-3">
						<div class="flex items-start gap-2">
							<FeatherIcon
								name="alert-triangle"
								class="h-4 w-4 text-danger-ink mt-0.5 shrink-0"
							/>
							<div class="text-xs text-danger-ink leading-relaxed">
								{{ adminMisconfigMessage }}
							</div>
						</div>
					</div>
				</template>
			</div>

			<div class="flex flex-col gap-2 px-4 pt-4">
				<Button class="w-full py-5 !bg-brand hover:!bg-brand !text-on-brand !border-none" variant="solid" @click="close">
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
	</GModal>
</template>

<script setup>
import GModal from "@/components/glass/GModal.vue"
import { computed, inject } from "vue"
import { FeatherIcon, Button } from "frappe-ui"
import { formatAccuracy } from "@/utils/geolocation"

const __ = inject("$translate")

const props = defineProps({
	isOpen: { type: Boolean, default: false },
	reason: {
		type: String,
		default: "outside_radius",
		// "outside_radius" | "no_shift_location" | "no_radius" | "imprecise_location"
	},
	shiftType: { type: String, default: "" },
	shiftLocation: { type: String, default: "" },
	distanceM: { type: Number, default: 0 },
	radiusM: { type: Number, default: 0 },
	overshootM: { type: Number, default: 0 },
	accuracyM: { type: Number, default: 0 },
})

const emit = defineEmits(["close"])

const title = computed(() => {
	switch (props.reason) {
		case "no_shift_location":
			return __("Check-in unavailable")
		case "no_radius":
			return __("Check-in unavailable")
		case "imprecise_location":
			return __("Location not precise enough")
		default:
			return __("Check-in blocked")
	}
})

const subtitle = computed(() => {
	switch (props.reason) {
		case "no_shift_location":
		case "no_radius":
			return __("Your shift is configured for strict geofencing but isn't ready yet.")
		case "imprecise_location":
			// Deliberately not "you are N metres away". The reading was too
			// coarse to place anyone, so a distance drawn from it would be an
			// accusation the data cannot support.
			return __("Your device could not pin down where you are accurately enough to check you in.")
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

const formattedAccuracy = computed(() => formatAccuracy(props.accuracyM) || __("unknown"))

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
