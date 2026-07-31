<template>
	<div class="flex flex-col w-full">
		<div class="m-kicker">
			{{ dayjs().format("dddd, D MMMM YYYY").toUpperCase() }}
		</div>
		<h1
			class="text-[30px] lg:text-[36px] leading-[1.08] tracking-[-0.015em] text-inkbase mt-2 mb-1.5"
		>
			{{ __("Hey, {0} 👋", [employee?.data?.first_name]) }}
		</h1>

		<template v-if="settings.data?.allow_employee_checkin_from_mobile_app">
			<div class="text-[13px] text-ink-600" v-if="lastLog">
				<span>{{ __("Last {0} was at {1}", [__(lastLogType), formatTimestamp(lastLog.time)]) }}</span>
				<span class="whitespace-pre"> &middot; </span>
				<router-link :to="{ name: 'EmployeeCheckinListView' }" v-slot="{ navigate }">
					<span @click="navigate" class="underline underline-offset-[3px] text-ink-800">{{ __("View List") }}</span>
				</router-link>
			</div>

			<!-- Forgot-to-check-out banner: open IN past 6 AM cutoff OR tagged abandoned by nightly sweeper -->
			<div
				v-if="hasStaleOpenIn"
				class="mt-3.5 flex flex-row items-center gap-3 border border-accent border-l-4 bg-accent-100 px-3 py-2.5 cursor-pointer"
				@click="lateCheckoutOpen = true"
			>
				<FeatherIcon
					:name="isAbandoned ? 'alert-triangle' : 'clock'"
					class="h-4 w-4 shrink-0 text-accent-800"
				/>
				<div class="flex flex-col flex-1 min-w-0 gap-0.5">
					<div class="text-[12.5px] font-semibold text-accent-800">
						<template v-if="isAbandoned">
							{{ __("HR flagged your {0} check-in as abandoned", [formatTimestamp(lastLog?.time)]) }}
						</template>
						<template v-else>
							{{ __("Forgot to check out from {0}?", [formatTimestamp(lastLog?.time)]) }}
						</template>
					</div>
					<div class="text-[11px] text-accent-800/80">
						<template v-if="isAbandoned">
							{{ __("Submit a late check-out now to resolve.") }}
						</template>
						<template v-else>
							{{ __("Tap to submit a late check-out for approval.") }}
						</template>
					</div>
				</div>
				<span class="m-chip m-chip-solid shrink-0">{{ __("Resolve") }}</span>
			</div>

			<button
				id="open-checkin-modal"
				class="m-btn-primary mt-5"
				@click="handleEmployeeCheckin"
			>
				<span>{{ nextAction.label }}</span>
				<FeatherIcon name="arrow-right" class="w-[17px] h-[17px] ml-auto" />
			</button>
		</template>

		<div v-else class="text-[13px] text-ink-600 mt-1">
			{{ dayjs().format("ddd, D MMMM, YYYY") }}
		</div>
	</div>

	<ion-modal
		v-if="settings.data?.allow_employee_checkin_from_mobile_app"
		ref="modal"
		class="checkin-sheet"
		trigger="open-checkin-modal"
		:initial-breakpoint="1"
		:breakpoints="[0, 1]"
		@ionModalDidPresent="onModalPresent"
		@ionModalWillDismiss="onModalDismiss"
	>
		<div class="w-full flex flex-col gap-4 px-4 pt-6 pb-8 border-t-[3px] border-inkbase bg-ground">
			<div class="flex flex-col gap-1">
				<div class="m-kicker">{{ nextAction.label }}</div>
				<div class="font-extrabold text-[36px] leading-[1.05] tabular-nums text-inkbase">
					{{ dayjs(checkinTimestamp).format("hh:mm:ss a") }}
				</div>
				<div class="text-xs text-ink-600">
					{{ dayjs().format("D MMM, YYYY") }}
				</div>
			</div>

			<template v-if="settings.data?.allow_geolocation_tracking">
				<div class="w-full flex flex-row items-center justify-between text-xs">
					<span class="text-ink-600">{{ locationStatus }}</span>
					<span
						v-if="shiftLocation.data && distanceToShift !== null"
						class="font-mono font-semibold tabular-nums"
						:class="
							isInsideRadius
								? 'text-accent-700'
								: 'text-inkbase'
						"
					>
						{{ formattedDistanceToShift }}
					</span>
				</div>

				<div
					ref="mapEl"
					class="border border-divider translate-z-0 block overflow-hidden w-full"
					style="height: 200px; z-index: 0;"
				></div>
			</template>

			<!-- Live selfie preview — camera auto-starts when the modal opens;
			     Confirm tap captures the frame, uploads, and submits the log
			     in one action (mirrors the React CheckInDialog UX). -->
			<div class="w-full flex flex-col items-center gap-2">
				<div
					class="overflow-hidden w-full relative border border-divider"
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

			<button
				:disabled="cameraStatus === 'starting' || checkins.insert.loading || cameraStatus === 'submitting'"
				class="m-btn-primary disabled:opacity-60"
				@click="submitLog(nextAction.action)"
			>
				<span>{{ __("Confirm {0}", [nextAction.label]) }}</span>
				<FeatherIcon
					:name="(checkins.insert.loading || cameraStatus === 'submitting') ? 'loader' : 'check'"
					class="w-[17px] h-[17px] ml-auto"
					:class="(checkins.insert.loading || cameraStatus === 'submitting') && 'animate-spin'"
				/>
			</button>
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
import { computed, inject, nextTick, ref, onMounted, onBeforeUnmount, watch } from "vue"
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

// Live check-in map state — initialised when the modal presents,
// torn down on dismiss. See onModalPresent / onModalDismiss.
const mapEl = ref(null)
let leafletMap = null
let userMarker = null
let shiftMarker = null
let radiusCircle = null
let geoWatchId = null
// Per-modal-session geolocation state. latitude/longitude refs persist across
// modal open/close, so "do we have a fix yet" must NOT be derived from them —
// both are reset in fetchLocation() each time the modal opens.
let hasSessionFix = false
let coarseFallbackRequested = false

const shiftLocation = createResource({
	url: "hrms.api.geofence.get_active_shift_location",
	makeParams() {
		return { employee: employee.data.name }
	},
})

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
	url: "hrms.api.geofence.check_geofence",
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
	const row = checkins.data[0]
	// Diagnostic for the "Last check-out shown after a check-in" bug — when
	// the displayed log_type doesn't match what the user just submitted, the
	// console row is the first thing to look at: did the IN reach the SPA?
	// Cheap, runs once per checkins reload.
	if (row) {
		console.info(
			"[CheckInPanel] lastLog resolved:",
			{
				name: row.name,
				log_type: row.log_type,
				time: row.time,
				requires_remote_approval: row.requires_remote_approval,
				is_abandoned: row.is_abandoned,
			}
		)
	}
	return row
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

	const firstFixThisSession = !hasSessionFix
	hasSessionFix = true
	updateUserMarker()
	// On reopen the marker already exists at last session's stale coords, so
	// the creation-time recenter doesn't fire — re-fit on this session's
	// first real fix instead.
	if (firstFixThisSession) fitMapBounds()
}

function handleLocationError(error) {
	locationStatus.value = "Unable to retrieve your location"
	if (error) locationStatus.value += `: ERROR(${error.code}): ${error.message}`
	console.warn("[CheckInPanel] geolocation error:", error)

	// High-accuracy watch timed out before any fix (common on Android
	// indoors): grab one coarse network-based position so the map still
	// centers on the user instead of staying on the fallback view. One
	// attempt per modal session (watch TIMEOUT recurs every ~15s), and
	// re-checked at resolution so a slower coarse result never overwrites
	// a real fix that landed in the meantime.
	if (!hasSessionFix && !coarseFallbackRequested && navigator.geolocation) {
		coarseFallbackRequested = true
		navigator.geolocation.getCurrentPosition(
			(position) => {
				if (!hasSessionFix) handleLocationSuccess(position)
			},
			() => {},
			{ enableHighAccuracy: false, maximumAge: 300000, timeout: 10000 }
		)
	}
}

const fetchLocation = () => {
	if (!navigator.geolocation) {
		locationStatus.value = __("Geolocation is not supported by your current browser")
		return
	}
	locationStatus.value = __("Locating...")
	hasSessionFix = false
	coarseFallbackRequested = false
	// watchPosition gives us live updates while the modal is open so the
	// user pin moves in real time as the device's GPS drifts/refines.
	if (geoWatchId !== null) {
		navigator.geolocation.clearWatch(geoWatchId)
	}
	// maximumAge 60s: Android's high-accuracy provider cold-starts slowly and
	// with maximumAge 0 even a seconds-old cached fix is rejected, so indoor
	// users timed out with no pin at all. A recent cached fix is fine for a
	// check-in radius measured in tens of meters.
	geoWatchId = navigator.geolocation.watchPosition(
		handleLocationSuccess,
		handleLocationError,
		{ enableHighAccuracy: true, maximumAge: 60000, timeout: 15000 }
	)
}

function stopWatchingLocation() {
	if (geoWatchId !== null && navigator.geolocation) {
		navigator.geolocation.clearWatch(geoWatchId)
		geoWatchId = null
	}
}

// ---------------------------------------------------------------------------
// Leaflet map — shift location pin + radius circle + live user pin
// ---------------------------------------------------------------------------

const distanceToShift = computed(() => {
	const loc = shiftLocation.data
	if (!loc || !latitude.value || !longitude.value) return null
	if (!window.L) return null
	return window.L.latLng(loc.latitude, loc.longitude).distanceTo(
		window.L.latLng(latitude.value, longitude.value)
	)
})

const isInsideRadius = computed(() => {
	const loc = shiftLocation.data
	const d = distanceToShift.value
	if (!loc || d === null) return false
	return loc.checkin_radius > 0 && d <= loc.checkin_radius
})

const formattedDistanceToShift = computed(() => {
	const d = distanceToShift.value
	if (d === null) return ""
	const label = isInsideRadius.value ? __("inside") : __("from office")
	return d >= 1000 ? `${(d / 1000).toFixed(2)} km ${label}` : `${Math.round(d)} m ${label}`
})

async function initMap() {
	// Leaflet is loaded via <script> in index.html. If the network hiccups,
	// retry a couple of times before giving up — never block the check-in.
	// 5s budget: on slow mobile radios the deferred CDN script can easily
	// take longer than the 1s this used to wait.
	for (let i = 0; i < 50; i++) {
		if (window.L) break
		await new Promise((r) => setTimeout(r, 100))
	}
	if (!window.L) {
		console.warn("[CheckInPanel] Leaflet not available; map will be skipped")
		return
	}
	if (!mapEl.value || leafletMap) return

	const loc = shiftLocation.data
	const center = loc
		? [loc.latitude, loc.longitude]
		: latitude.value && longitude.value
			? [latitude.value, longitude.value]
			: [3.139, 101.6869] // KL fallback so the tile layer renders something
	const zoom = loc ? 16 : 13

	leafletMap = window.L.map(mapEl.value, {
		zoomControl: false,
		attributionControl: false,
		dragging: true,
		tap: true,
		// Android Chrome/WebView intermittently fails to composite the SVG
		// overlay pane inside the transformed modal container, leaving the
		// radius circle invisible; the canvas renderer is immune.
		preferCanvas: true,
	}).setView(center, zoom)

	window.L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
		maxZoom: 19,
	}).addTo(leafletMap)

	if (loc) {
		const shiftLatLng = window.L.latLng(loc.latitude, loc.longitude)
		shiftMarker = window.L.marker(shiftLatLng, {
			title: loc.label,
		}).addTo(leafletMap)
		shiftMarker.bindTooltip(loc.label || __("Shift Location"), {
			permanent: true,
			direction: "top",
			offset: [0, -28],
			className: "shift-loc-tooltip",
		})
		if (loc.checkin_radius > 0) {
			radiusCircle = window.L.circle(shiftLatLng, {
				radius: loc.checkin_radius,
				color: loc.strict ? "#dc2626" : "#2563eb",
				weight: 2,
				fillColor: loc.strict ? "#dc2626" : "#3b82f6",
				fillOpacity: 0.12,
			}).addTo(leafletMap)
		}
	}

	updateUserMarker()
	fitMapBounds()

	// The ion-modal sheet can still be settling when Leaflet measures the
	// container (Android animates longer than the deferred tick) — re-measure
	// after the animation so tiles and overlays aren't offset from the view.
	setTimeout(() => {
		if (leafletMap) {
			leafletMap.invalidateSize()
			fitMapBounds()
		}
	}, 400)
}

function updateUserMarker() {
	if (!leafletMap || !window.L) return
	if (!latitude.value || !longitude.value) return

	const here = window.L.latLng(latitude.value, longitude.value)
	if (!userMarker) {
		// Custom blue dot — Leaflet's default icon is a tall pin which reads
		// awkwardly for "this is you right now"; a dot is the convention.
		const dotIcon = window.L.divIcon({
			className: "user-pin",
			html: '<div class="user-pin-dot"></div><div class="user-pin-ring"></div>',
			iconSize: [22, 22],
			iconAnchor: [11, 11],
		})
		userMarker = window.L.marker(here, {
			icon: dotIcon,
			title: __("You"),
			zIndexOffset: 1000,
		}).addTo(leafletMap)
		// On Android the first GPS fix usually lands after initMap already
		// centered the map (fallback or office) — bring the new pin and the
		// radius circle into one view. Later fixes only move the pin so we
		// don't fight the user's own panning.
		fitMapBounds()
	} else {
		userMarker.setLatLng(here)
	}
}

function fitMapBounds() {
	if (!leafletMap || !window.L) return
	const points = []
	if (shiftMarker) points.push(shiftMarker.getLatLng())
	if (userMarker) points.push(userMarker.getLatLng())
	if (points.length === 2) {
		leafletMap.fitBounds(window.L.latLngBounds(points), {
			padding: [40, 40],
			maxZoom: 17,
		})
	} else if (points.length === 1) {
		leafletMap.setView(points[0], 16)
	}
}

function destroyMap() {
	if (leafletMap) {
		leafletMap.remove()
		leafletMap = null
	}
	userMarker = null
	shiftMarker = null
	radiusCircle = null
}

// If the shift-location fetch finishes after the map is already up
// (slow network on first open), paint the pin + circle now.
watch(
	() => shiftLocation.data,
	(loc) => {
		if (!leafletMap || !window.L || !loc) return
		if (!shiftMarker) {
			const shiftLatLng = window.L.latLng(loc.latitude, loc.longitude)
			shiftMarker = window.L.marker(shiftLatLng).addTo(leafletMap)
			shiftMarker.bindTooltip(loc.label || __("Shift Location"), {
				permanent: true,
				direction: "top",
				offset: [0, -28],
				className: "shift-loc-tooltip",
			})
			if (loc.checkin_radius > 0) {
				radiusCircle = window.L.circle(shiftLatLng, {
					radius: loc.checkin_radius,
					color: loc.strict ? "#dc2626" : "#2563eb",
					weight: 2,
					fillColor: loc.strict ? "#dc2626" : "#3b82f6",
					fillOpacity: 0.12,
				}).addTo(leafletMap)
			}
			fitMapBounds()
		}
	}
)

const handleEmployeeCheckin = () => {
	checkinTimestamp.value = dayjs().format("YYYY-MM-DD HH:mm:ss")

	if (settings.data?.allow_geolocation_tracking) {
		// Kick off the shift-location fetch + live geolocation in parallel.
		// The map waits for one of them via initMap(); whichever arrives first
		// renders, the second updates in-place.
		shiftLocation.reload()
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

			// Refresh the log list so lastLog (and the stale "Forgot to check out"
			// banner / button state) reflect the log just inserted. The socket
			// list_update handler also reloads, but it's unreliable on mobile
			// (disconnected/backgrounded), so reload explicitly like the dialogs do.
			checkins.reload()

			if (doc?.requires_remote_approval) {
				try {
					const rows = await fetchRemoteRequest.submit({ checkin: doc.name })
					const req = rows?.[0]
					// OUT logs that inherit a same-day Approved IN land here
					// already in status=Approved (auto-inherit by
					// create_remote_request_if_needed). Don't pop the reason
					// dialog for those — there's nothing left to decide.
					if (req && req.status === "Pending") {
						remoteRequest.value = {
							name: req.name,
							logType: req.log_type || logType,
							distanceM: Number(req.distance_m) || 0,
							approverName: req.approver || "",
						}
						remoteDialogOpen.value = true
						return
					}
					if (req && req.status === "Approved") {
						toast({
							title: __("{0} approved", [actionLabel]),
							text: __("Inherited from your earlier approved check-in."),
							icon: "check-circle",
							position: "bottom-center",
							iconClasses: "text-green-500",
						})
						return
					}
					if (req && req.status === "Rejected") {
						toast({
							title: __("{0} blocked", [actionLabel]),
							text: __(
								"A prior remote check-in request today was rejected — please contact HR."
							),
							icon: "alert-circle",
							position: "bottom-center",
							iconClasses: "text-red-500",
						})
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
	// Defer one tick so the map container has its final size before Leaflet
	// measures it. Without this, the tile layer renders at 0x0 on first paint.
	nextTick(() => {
		if (settings.data?.allow_geolocation_tracking) {
			initMap()
		}
	})
}

function onModalDismiss() {
	stopCamera()
	cameraStatus.value = "idle"
	cameraError.value = null
	stopWatchingLocation()
	destroyMap()
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
	stopWatchingLocation()
	destroyMap()
})
</script>

<style>
/* Live "you are here" pin — solid blue dot with a pulsing outer ring. */
.user-pin { position: relative; width: 22px; height: 22px; }
.user-pin-dot {
	position: absolute;
	top: 50%;
	left: 50%;
	width: 14px;
	height: 14px;
	margin: -7px 0 0 -7px;
	border-radius: 50%;
	background: #2563eb;
	border: 2px solid #ffffff;
	box-shadow: 0 0 0 1px rgba(37, 99, 235, 0.4);
}
.user-pin-ring {
	position: absolute;
	top: 50%;
	left: 50%;
	width: 22px;
	height: 22px;
	margin: -11px 0 0 -11px;
	border-radius: 50%;
	border: 2px solid rgba(37, 99, 235, 0.6);
	animation: user-pin-pulse 2s ease-out infinite;
}
@keyframes user-pin-pulse {
	0%   { transform: scale(0.8); opacity: 0.9; }
	100% { transform: scale(2.2); opacity: 0; }
}

/* Shift-location label sitting above its pin. */
.shift-loc-tooltip {
	background: #111827 !important;
	color: #f9fafb !important;
	border: none !important;
	font-size: 11px !important;
	font-weight: 600 !important;
	padding: 2px 6px !important;
	border-radius: 4px !important;
	box-shadow: 0 1px 2px rgba(0, 0, 0, 0.25) !important;
}
.shift-loc-tooltip:before { display: none !important; }

/* On tablet/desktop the check-in sheet presents as a centered dialog.
   Centering comes from the global modal-sheet rule in modernist.css —
   adding transforms here double-centers and pushes the dialog off-screen.
   Only the narrower width and internal scroll are set per-modal. */
@media (min-width: 640px) {
	ion-modal.checkin-sheet {
		--width: min(460px, 92vw);
	}
	ion-modal.checkin-sheet::part(content) {
		max-height: 88vh;
		overflow-y: auto;
	}
}
</style>
