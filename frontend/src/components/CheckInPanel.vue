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

			<!-- Selfie capture: optional photo evidence per check-in (mirrors the
			     React CheckInDialog used in ncig-merchandiser POS). -->
			<div class="w-full flex flex-col items-center gap-2">
				<template v-if="cameraStatus === 'idle'">
					<Button
						variant="outline"
						class="w-full py-3 text-sm"
						@click="startCamera"
					>
						<template #prefix>
							<FeatherIcon name="camera" class="w-4" />
						</template>
						{{ __("Take Selfie") }}
					</Button>
				</template>

				<template v-else-if="cameraStatus === 'live'">
					<div
						class="rounded overflow-hidden w-full"
						style="aspect-ratio: 4 / 3; background: #000;"
					>
						<video
							ref="videoEl"
							autoplay
							playsinline
							muted
							class="w-full h-full object-cover"
							style="transform: scaleX(-1);"
						></video>
					</div>
					<Button
						variant="solid"
						class="w-full py-3 text-sm"
						@click="takeSelfie"
					>
						<template #prefix>
							<FeatherIcon name="aperture" class="w-4" />
						</template>
						{{ __("Capture") }}
					</Button>
				</template>

				<template v-else>
					<div
						class="rounded overflow-hidden w-full"
						style="aspect-ratio: 4 / 3; background: #000;"
					>
						<img
							v-if="selfieDataUrl"
							:src="selfieDataUrl"
							alt="selfie preview"
							class="w-full h-full object-cover"
						/>
					</div>
					<Button
						variant="outline"
						class="w-full py-3 text-sm"
						:disabled="cameraStatus === 'uploading'"
						@click="retakeSelfie"
					>
						<template #prefix>
							<FeatherIcon name="refresh-cw" class="w-4" />
						</template>
						{{ cameraStatus === "uploading" ? __("Uploading...") : __("Retake") }}
					</Button>
				</template>

				<canvas ref="canvasEl" class="hidden"></canvas>

				<div v-if="cameraError" class="text-xs text-red-500 text-center">
					{{ cameraError }}
				</div>
			</div>

			<Button
				:loading="checkins.insert.loading || cameraStatus === 'uploading'"
				variant="solid"
				class="w-full py-5 text-sm disabled:bg-gray-700"
				@click="submitLog(nextAction.action)"
			>
				{{ __("Confirm {0}", [nextAction.label]) }}
			</Button>
		</div>
	</ion-modal>
</template>

<script setup>
import { createResource, createListResource, toast, FeatherIcon } from "frappe-ui"
import { computed, inject, nextTick, ref, onMounted, onBeforeUnmount } from "vue"
import { IonModal, modalController } from "@ionic/vue"

import { formatTimestamp } from "@/utils/formatters"

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
// idle | live | uploading | captured
const cameraStatus = ref("idle")
const selfieDataUrl = ref(null)
const selfieFileUrl = ref(null)
const cameraError = ref(null)
const settings = createResource({
	url: "hrms.api.get_hr_settings",
	auto: true,
})

const checkins = createListResource({
	doctype: DOCTYPE,
	fields: ["name", "employee", "employee_name", "log_type", "time", "device_id"],
	filters: {
		employee: employee.data.name,
	},
	orderBy: "time desc",
})
checkins.reload()

const lastLog = computed(() => {
	if (checkins.list.loading || !checkins.data) return {}
	return checkins.data[0]
})

const lastLogType = computed(() => {
	return lastLog?.value?.log_type === "IN" ? "check-in" : "check-out"
})

const nextAction = computed(() => {
	return lastLog?.value?.log_type === "IN"
		? { action: "OUT", label: __("Check Out") }
		: { action: "IN", label: __("Check In") }
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

const submitLog = (logType) => {
	const actionLabel = logType === "IN" ? __("Check-in") : __("Check-out")
	const payload = {
		employee: employee.data.name,
		log_type: logType,
		time: checkinTimestamp.value,
		latitude: latitude.value,
		longitude: longitude.value,
	}
	if (selfieFileUrl.value) {
		payload.selfie_image = selfieFileUrl.value
	}

	checkins.insert.submit(payload, {
		onSuccess() {
			modalController.dismiss()
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
	if (!navigator.mediaDevices?.getUserMedia) {
		cameraError.value = __("Camera not supported on this device")
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
	}
}

function stopCamera() {
	if (cameraStream) {
		cameraStream.getTracks().forEach((t) => t.stop())
		cameraStream = null
		console.info("[Selfie] Camera stopped")
	}
}

async function takeSelfie() {
	const video = videoEl.value
	const canvas = canvasEl.value
	if (!video || !canvas || !video.videoWidth) {
		console.warn("[Selfie] Video not ready")
		return
	}
	canvas.width = video.videoWidth
	canvas.height = video.videoHeight
	const ctx = canvas.getContext("2d")
	// Mirror the front-camera frame so the saved image matches the preview.
	ctx.translate(canvas.width, 0)
	ctx.scale(-1, 1)
	ctx.drawImage(video, 0, 0)
	ctx.setTransform(1, 0, 0, 1, 0, 0)

	selfieDataUrl.value = canvas.toDataURL("image/jpeg", 0.8)
	stopCamera()
	cameraStatus.value = "uploading"
	await uploadSelfie(selfieDataUrl.value)
}

async function retakeSelfie() {
	selfieDataUrl.value = null
	selfieFileUrl.value = null
	cameraStatus.value = "idle"
	cameraError.value = null
	await startCamera()
}

async function uploadSelfie(dataUrl) {
	try {
		const blob = await (await fetch(dataUrl)).blob()
		const filename = `selfie-${employee.data.name}-${Date.now()}.jpg`
		const file = new File([blob], filename, { type: "image/jpeg" })
		const fd = new FormData()
		fd.append("file", file, filename)
		fd.append("is_private", "0")
		fd.append("doctype", DOCTYPE)
		fd.append("fieldname", "selfie_image")

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
		selfieFileUrl.value = out.message.file_url
		cameraStatus.value = "captured"
		console.info("[Selfie] Uploaded:", selfieFileUrl.value)
	} catch (err) {
		console.error("[Selfie] Upload error:", err)
		cameraError.value = __("Failed to upload selfie: {0}", [err.message || err])
		// Keep the preview so the user can retake or skip.
		cameraStatus.value = "captured"
	}
}

function onModalDismiss() {
	stopCamera()
	selfieDataUrl.value = null
	selfieFileUrl.value = null
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
