<template>
	<div class="flex flex-col bg-white rounded w-full py-6 px-4 border-none">
		<h2 class="text-lg font-bold text-gray-900">
			{{ __("Hey, {0} 👋", [employee?.data?.first_name]) }}
		</h2>

		<template v-if="settings.data?.allow_employee_checkin_from_mobile_app">
			<div class="font-medium text-sm text-gray-500 mt-1.5" v-if="lastLog">
				<span>{{ __("Last {0} was at {1}", [__(lastLogType), formatTimestamp(lastLog.time)]) }}</span>
				<span class="whitespace-pre"> &middot; </span>
				<router-link :to="{ name: 'EmployeeCheckinListView' }" v-slot="{ navigate }">
					<span @click="navigate" class="underline">View List</span>
				</router-link>
			</div>

			<!-- Forgot-to-check-out banner: open IN past 6 AM cutoff OR tagged abandoned by nightly sweeper -->
			<div
				v-if="hasStaleOpenIn"
				class="mt-4 flex flex-row items-center gap-3 rounded-md px-3 py-2 cursor-pointer border"
				:class="
					isAbandoned
						? 'bg-red-50 border-red-200'
						: 'bg-orange-50 border-orange-200'
				"
				@click="lateCheckoutOpen = true"
			>
				<FeatherIcon
					:name="isAbandoned ? 'alert-triangle' : 'clock'"
					class="h-4 w-4 shrink-0"
					:class="isAbandoned ? 'text-red-600' : 'text-orange-600'"
				/>
				<div class="flex flex-col flex-1 min-w-0">
					<div
						class="text-sm font-semibold"
						:class="isAbandoned ? 'text-red-800' : 'text-orange-800'"
					>
						<template v-if="isAbandoned">
							{{ __("HR flagged your {0} check-in as abandoned", [formatTimestamp(lastLog?.time)]) }}
						</template>
						<template v-else>
							{{ __("Forgot to check out from {0}?", [formatTimestamp(lastLog?.time)]) }}
						</template>
					</div>
					<div
						class="text-xs"
						:class="isAbandoned ? 'text-red-700' : 'text-orange-700'"
					>
						<template v-if="isAbandoned">
							{{ __("Submit a late check-out now to resolve.") }}
						</template>
						<template v-else>
							{{ __("Tap to submit a late check-out for approval.") }}
						</template>
					</div>
				</div>
				<FeatherIcon
					name="chevron-right"
					class="h-4 w-4 shrink-0"
					:class="isAbandoned ? 'text-red-500' : 'text-orange-500'"
				/>
			</div>

			<Button
				class="mt-4 mb-1 drop-shadow-sm py-5 text-base"
				id="open-checkin-modal"
				@click="handleEmployeeCheckin"
			>
				<template #prefix>
					<FeatherIcon
						:name="nextAction.action === 'IN' ? 'arrow-right-circle' : 'arrow-left-circle'"
						class="w-4"
					/>
				</template>
				{{ nextAction.label }}
			</Button>
		</template>

		<div v-else class="font-medium text-sm text-gray-500 mt-1.5">
			{{ dayjs().format("ddd, D MMMM, YYYY") }}
		</div>
	</div>

	<ion-modal
		v-if="settings.data?.allow_employee_checkin_from_mobile_app"
		ref="modal"
		trigger="open-checkin-modal"
		:initial-breakpoint="1"
		:breakpoints="[0, 1]"
		@ionModalDidPresent="onModalPresent"
		@ionModalWillDismiss="onModalDismiss"
	>
		<div class="h-120 w-full flex flex-col items-center justify-center gap-4 p-4 mb-5">
			<div class="flex flex-col gap-1.5 mt-2 items-center justify-center">
				<div class="font-bold text-xl">
					{{ dayjs(checkinTimestamp).format("hh:mm:ss a") }}
				</div>
				<div class="font-medium text-gray-500 text-sm">
					{{ dayjs().format("D MMM, YYYY") }}
				</div>
			</div>

			<template v-if="settings.data?.allow_geolocation_tracking">
				<span v-if="locationStatus" class="font-medium text-gray-500 text-sm">
					{{ locationStatus }}
				</span>

				<div class="rounded border-4 translate-z-0 block overflow-hidden w-full h-170">
					<iframe
						width="100%"
						height="170"
						frameborder="0"
						scrolling="no"
						marginheight="0"
						marginwidth="0"
						style="border: 0"
						:src="`https://maps.google.com/maps?q=${latitude},${longitude}&hl=en&z=15&amp;output=embed`"
					>
					</iframe>
				</div>
			</template>

			<!-- Live selfie preview — camera auto-starts when the modal opens;
			     Confirm tap captures the frame, uploads, and submits the log
			     in one action (mirrors the React CheckInDialog UX). -->
			<div class="w-full flex flex-col items-center gap-2">
				<div
					class="rounded overflow-hidden w-full relative"
					style="aspect-ratio: 4 / 3; background: #000;"
				>
					<video
						v-show="cameraStatus === 'live' || cameraStatus === 'submitting'"
						ref="videoEl"
						autoplay
						playsinline
						muted
						class="w-full h-full object-cover"
						style="transform: scaleX(-1);"
					></video>
					<div
						v-if="cameraStatus === 'starting'"
						class="absolute inset-0 flex items-center justify-center text-white text-xs"
					>
						{{ __("Starting camera...") }}
					</div>
					<div
						v-else-if="cameraStatus === 'error'"
						class="absolute inset-0 flex items-center justify-center text-white text-xs text-center px-4"
					>
						<span>{{ cameraError }}</span>
					</div>
				</div>
				<canvas ref="canvasEl" class="hidden"></canvas>
			</div>

			<Button
				:loading="checkins.insert.loading || cameraStatus === 'submitting'"
				:disabled="cameraStatus === 'starting'"
				variant="solid"
				class="w-full py-5 text-sm disabled:bg-gray-700"
				@click="submitLog(nextAction.action)"
			>
				{{ __("Confirm {0}", [nextAction.label]) }}
			</Button>
		</div>
	</ion-modal>

	<RemoteCheckinDialog
		:is-open="remoteDialogOpen"
		:request-name="remoteRequest.name"
		:log-type="remoteRequest.logType"
		:distance-m="remoteRequest.distanceM"
		:approver-name="remoteRequest.approverName"
		@close="remoteDialogOpen = false"
		@submitted="checkins.reload()"
	/>

	<StrictRejectionDialog
		:is-open="strictDialogOpen"
		:reason="strictRejection.reason"
		:shift-type="strictRejection.shiftType"
		:shift-location="strictRejection.shiftLocation"
		:distance-m="strictRejection.distanceM"
		:radius-m="strictRejection.radiusM"
		:overshoot-m="strictRejection.overshootM"
		@close="strictDialogOpen = false"
	/>

	<LateCheckoutDialog
		:is-open="lateCheckoutOpen"
		:in-checkin-name="lastLog?.name || ''"
		:in-checkin-time="lastLog?.time || ''"
		@close="lateCheckoutOpen = false"
		@submitted="checkins.reload()"
	/>
</template>

<script setup>
import { createResource, createListResource, toast, FeatherIcon } from "frappe-ui"
import { computed, inject, nextTick, ref, onMounted, onBeforeUnmount } from "vue"
import { IonModal, modalController } from "@ionic/vue"

import { formatTimestamp } from "@/utils/formatters"
import RemoteCheckinDialog from "@/components/RemoteCheckinDialog.vue"
import StrictRejectionDialog from "@/components/StrictRejectionDialog.vue"
import LateCheckoutDialog from "@/components/LateCheckoutDialog.vue"

const DOCTYPE = "Employee Checkin"

const socket = inject("$socket")
const employee = inject("$employee")
const dayjs = inject("$dayjs")
const __ = inject("$translate")
const checkinTimestamp = ref(null)
const latitude = ref(0)
const longitude = ref(0)
const locationStatus = ref("")

// Selfie capture state
const videoEl = ref(null)
const canvasEl = ref(null)
let cameraStream = null
// idle | starting | live | submitting | error
const cameraStatus = ref("idle")
const cameraError = ref(null)
const settings = createResource({
	url: "hrms.api.get_hr_settings",
	auto: true,
})

const checkins = createListResource({
	doctype: DOCTYPE,
	fields: [
		"name",
		"employee",
		"employee_name",
		"log_type",
		"time",
		"device_id",
		"requires_remote_approval",
		"remote_approval_status",
		"is_abandoned",
	],
	filters: {
		employee: employee.data.name,
	},
	orderBy: "time desc",
})
checkins.reload()

// Remote checkin dialog state
const remoteDialogOpen = ref(false)
const remoteRequest = ref({ name: "", logType: "IN", distanceM: 0, approverName: "" })

// Strict-mode rejection dialog state (used when the preflight tells us the
// server would throw CheckinRadiusExceededError — we abort the insert).
const strictDialogOpen = ref(false)
const strictRejection = ref({
	reason: "outside_radius",
	shiftType: "",
	shiftLocation: "",
	distanceM: 0,
	radiusM: 0,
	overshootM: 0,
})

const preflightGeofence = createResource({
	url: "nsty.api.geofence.check_geofence",
	makeParams(values) {
		return values
	},
})

// Late-checkout dialog state
const lateCheckoutOpen = ref(false)
const hasStaleOpenIn = computed(() => {
	const last = lastLog?.value
	return !!(last && last.log_type === "IN" && isSessionStale(last.time))
})
const isAbandoned = computed(() => !!lastLog?.value?.is_abandoned)

const fetchRemoteRequest = createResource({
	url: "frappe.client.get_list",
	makeParams(values) {
		return {
			doctype: "Remote Checkin Request",
			filters: { checkin: values.checkin },
			fields: [
				"name",
				"log_type",
				"distance_m",
				"approver",
				"status",
			],
			limit_page_length: 1,
		}
	},
})

const lastLog = computed(() => {
	if (checkins.list.loading || !checkins.data) return {}
	return checkins.data[0]
})

const lastLogType = computed(() => {
	return lastLog?.value?.log_type === "IN" ? "check-in" : "check-out"
})

// Sessions roll over at 06:00 local the day after check-in.
// If a user checks IN late at night, they can still check OUT during OT
// up until 06:00 the next morning. After that the open IN is treated as
// stale and the button flips back to "Check In".
const STALE_AFTER_HOUR = 6

function isSessionStale(checkinTime) {
	if (!checkinTime) return true
	const t = new Date(checkinTime)
	if (Number.isNaN(t.getTime())) return true
	const expiry = new Date(t)
	expiry.setDate(t.getDate() + 1)
	expiry.setHours(STALE_AFTER_HOUR, 0, 0, 0)
	return Date.now() >= expiry.getTime()
}

const nextAction = computed(() => {
	const last = lastLog?.value
	if (!last || last.log_type !== "IN" || isSessionStale(last.time)) {
		return { action: "IN", label: __("Check In") }
	}
	return { action: "OUT", label: __("Check Out") }
})

function handleLocationSuccess(position) {
	latitude.value = position.coords.latitude
	longitude.value = position.coords.longitude

	locationStatus.value = [
		__("Latitude: {0}°", [Number(latitude.value).toFixed(5)]),
		__("Longitude: {0}°", [Number(longitude.value).toFixed(5)]),
	].join(", ")
}

function handleLocationError(error) {
	locationStatus.value = "Unable to retrieve your location"
	if (error) locationStatus.value += `: ERROR(${error.code}): ${error.message}`
}

const fetchLocation = () => {
	if (!navigator.geolocation) {
		locationStatus.value = __("Geolocation is not supported by your current browser")
	} else {
		locationStatus.value = __("Locating...")
		navigator.geolocation.getCurrentPosition(handleLocationSuccess, handleLocationError)
	}
}

const handleEmployeeCheckin = () => {
	checkinTimestamp.value = dayjs().format("YYYY-MM-DD HH:mm:ss")

	if (settings.data?.allow_geolocation_tracking) {
		fetchLocation()
	}
}

const submitLog = async (logType) => {
	const actionLabel = logType === "IN" ? __("Check-in") : __("Check-out")

	// Preflight strict geofence: if the assigned Shift Type has
	// enable_strict_geofence and we're outside the radius (or the shift is
	// misconfigured), the server-side validate will throw. Catch this here
	// so the user sees the explanatory dialog instead of a generic toast.
	if (settings.data?.allow_geolocation_tracking && latitude.value && longitude.value) {
		try {
			const result = await preflightGeofence.submit({
				employee: employee.data.name,
				log_type: logType,
				latitude: latitude.value,
				longitude: longitude.value,
				time: checkinTimestamp.value,
			})
			if (result && result.ok === false && result.mode === "strict_block") {
				console.info("[Preflight] strict block:", result)
				stopCamera()
				modalController.dismiss()
				strictRejection.value = {
					reason: result.reason || "outside_radius",
					shiftType: result.shift_type || "",
					shiftLocation: result.shift_location || "",
					distanceM: Number(result.distance_m) || 0,
					radiusM: Number(result.radius_m) || 0,
					overshootM: Number(result.overshoot_m) || 0,
				}
				strictDialogOpen.value = true
				return
			}
		} catch (err) {
			// Preflight is advisory — if it fails, fall through and let the
			// real insert path enforce policy. Avoid blocking the user on a
			// transient network blip.
			console.warn("[Preflight] check_geofence failed, falling through:", err)
		}
	}

	// Capture + upload the selfie first, then submit the checkin with the
	// resulting file URL. If the camera failed to start (denied / no device)
	// we still allow the check-in to proceed without a photo so the user is
	// not locked out.
	let selfieUrl = null
	if (cameraStatus.value === "live") {
		cameraStatus.value = "submitting"
		try {
			const dataUrl = captureFrame()
			if (dataUrl) {
				selfieUrl = await uploadSelfie(dataUrl)
			}
		} catch (err) {
			console.error("[Selfie] Capture/upload error:", err)
			toast({
				title: __("Selfie failed"),
				text: err?.message || __("Could not attach selfie — proceeding without it."),
				icon: "alert-circle",
				position: "bottom-center",
				iconClasses: "text-red-500",
			})
		} finally {
			// Free the camera before the network round-trip for the checkin.
			stopCamera()
		}
	}

	const payload = {
		employee: employee.data.name,
		log_type: logType,
		time: checkinTimestamp.value,
		latitude: latitude.value,
		longitude: longitude.value,
	}
	if (selfieUrl) {
		payload.selfie_image = selfieUrl
	}

	checkins.insert.submit(payload, {
		async onSuccess(doc) {
			modalController.dismiss()

			if (doc?.requires_remote_approval) {
				try {
					const rows = await fetchRemoteRequest.submit({ checkin: doc.name })
					const req = rows?.[0]
					if (req) {
						remoteRequest.value = {
							name: req.name,
							logType: req.log_type || logType,
							distanceM: Number(req.distance_m) || 0,
							approverName: req.approver || "",
						}
						remoteDialogOpen.value = true
						return
					}
				} catch (err) {
					console.warn("[RemoteCheckin] could not load request:", err)
				}
			}

			toast({
				title: __("Success"),
				text: __("{0} successful!", [actionLabel]),
				icon: "check-circle",
				position: "bottom-center",
				iconClasses: "text-green-500",
			})
		},
		onError(error) {
			let messages = error.messages || []

			for (const message of messages) {
				toast({
					title: __("Error"),
					text: message || __("{0} failed!", [actionLabel]),
					icon: "alert-circle",
					position: "bottom-center",
					iconClasses: "text-red-500",
				})
			}
		},
	})
}

async function startCamera() {
	cameraError.value = null
	cameraStatus.value = "starting"
	if (!navigator.mediaDevices?.getUserMedia) {
		cameraError.value = __("Camera not supported on this device")
		cameraStatus.value = "error"
		return
	}
	try {
		cameraStream = await navigator.mediaDevices.getUserMedia({
			video: {
				facingMode: "user",
				width: { ideal: 640 },
				height: { ideal: 480 },
			},
		})
		cameraStatus.value = "live"
		await nextTick()
		if (videoEl.value) {
			videoEl.value.srcObject = cameraStream
		}
		console.info("[Selfie] Camera started")
	} catch (err) {
		console.error("[Selfie] Camera error:", err)
		cameraError.value = __("Camera access denied. Please allow camera permission.")
		cameraStatus.value = "error"
	}
}

function stopCamera() {
	if (cameraStream) {
		cameraStream.getTracks().forEach((t) => t.stop())
		cameraStream = null
		console.info("[Selfie] Camera stopped")
	}
}

function captureFrame() {
	const video = videoEl.value
	const canvas = canvasEl.value
	if (!video || !canvas || !video.videoWidth) {
		console.warn("[Selfie] Video not ready when capturing")
		return null
	}
	canvas.width = video.videoWidth
	canvas.height = video.videoHeight
	const ctx = canvas.getContext("2d")
	// Mirror the front-camera frame so the saved image matches the preview.
	ctx.translate(canvas.width, 0)
	ctx.scale(-1, 1)
	ctx.drawImage(video, 0, 0)
	ctx.setTransform(1, 0, 0, 1, 0, 0)
	return canvas.toDataURL("image/jpeg", 0.8)
}

async function uploadSelfie(dataUrl) {
	const blob = await (await fetch(dataUrl)).blob()
	const filename = `selfie-${employee.data.name}-${Date.now()}.jpg`
	const file = new File([blob], filename, { type: "image/jpeg" })
	const fd = new FormData()
	fd.append("file", file, filename)
	fd.append("is_private", "0")
	// Intentionally NOT setting doctype/docname/fieldname: the Employee Checkin
	// record doesn't exist yet, and passing doctype without a valid docname makes
	// Frappe error with "Attached To Name must be a string or an integer". The
	// file is created standalone; the returned file_url is then written onto the
	// new Employee Checkin via the insert payload's selfie_image field.

	const headers = { "X-Frappe-Site-Name": window.location.hostname }
	if (window.csrf_token) {
		headers["X-Frappe-CSRF-Token"] = window.csrf_token
	}

	const res = await fetch("/api/method/upload_file", {
		method: "POST",
		headers,
		body: fd,
	})
	const out = await res.json()
	if (!res.ok || !out?.message?.file_url) {
		throw new Error(out?.exception || __("Upload failed"))
	}
	console.info("[Selfie] Uploaded:", out.message.file_url)
	return out.message.file_url
}

function onModalPresent() {
	// Auto-start the camera as soon as the check-in sheet is fully open.
	startCamera()
}

function onModalDismiss() {
	stopCamera()
	cameraStatus.value = "idle"
	cameraError.value = null
}

onMounted(() => {
	socket.emit("doctype_subscribe", DOCTYPE)
	socket.on("list_update", (data) => {
		if (data.doctype == DOCTYPE) {
			checkins.reload()
		}
	})
})

onBeforeUnmount(() => {
	socket.emit("doctype_unsubscribe", DOCTYPE)
	socket.off("list_update")
	stopCamera()
})
</script>
