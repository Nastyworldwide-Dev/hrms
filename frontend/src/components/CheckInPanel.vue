<template>
	<div class="flex flex-col w-full">
		<!-- data-visual-mask: today's date, rots at midnight. -->
		<div class="g-eyebrow" data-visual-mask>
			{{ dayjs().format("dddd, D MMMM YYYY").toUpperCase() }}
		</div>
		<h1 class="text-display-number lg:text-clock text-inkbase mt-2 mb-1.5">
			{{ __("Hey, {0} 👋", [employee?.data?.first_name]) }}
		</h1>

		<!-- A failed settings read hides check-in entirely, and the employee standing
		     at the door has no way to tell that from the feature being switched off
		     for them. Of everything in this app that renders nothing on error, this
		     is the one that stops someone being paid correctly. -->
		<ResourceError :resource="settings" what="your check-in settings" />

		<template v-if="settings.data?.allow_employee_checkin_from_mobile_app">
			<div class="text-card-title text-ink-600" v-if="lastLog">
				<!-- data-visual-mask: formatTimestamp() returns "… yesterday" for one
				     day and "… on 20 Aug" the next, so the string changes with no
				     code change. Masked on the span only, not the row. -->
				<span data-visual-mask>{{
					__("Last {0} was at {1}", [__(lastLogType), formatTimestamp(lastLog.time)])
				}}</span>
				<span class="whitespace-pre"> &middot; </span>
				<router-link :to="{ name: 'EmployeeCheckinListView' }" v-slot="{ navigate }">
					<span @click="navigate" class="g-seclink underline underline-offset-link text-ink-800">{{
						__("View List")
					}}</span>
				</router-link>
			</div>

			<!-- Forgot-to-check-out banner: open IN past 6 AM cutoff OR tagged abandoned by nightly sweeper -->
			<!-- 8.5 — was a hand-rolled div carrying Modernist utilities:
			     `bg-accent-100` with `text-accent-800` copy. In dark theme both
			     resolve to the accent itself, so this rendered as a blank
			     chartreuse block — text at a MEASURED 1.00 contrast ratio,
			     present in the DOM and completely invisible. It is a warning
			     banner, and the system already had one. -->
			<GBanner
				v-if="hasStaleOpenIn"
				variant="warning"
				class="g-banner--tappable mt-3.5"
				@click="lateCheckoutOpen = true"
			>
				<div class="flex flex-row items-center gap-3">
					<FeatherIcon :name="isAbandoned ? 'alert-triangle' : 'clock'" class="h-4 w-4 shrink-0" />
					<div class="flex flex-col flex-1 min-w-0">
						<!-- data-visual-mask: both branches embed formatTimestamp(), whose
						     wording changes as the check-in ages. -->
						<span class="g-banner__title" data-visual-mask>
							<template v-if="isAbandoned">
								{{
									__("HR flagged your {0} check-in as abandoned", [
										formatTimestamp(unresolvedStaleIn.data?.time),
									])
								}}
							</template>
							<template v-else>
								{{
									__("Forgot to check out from {0}?", [
										formatTimestamp(unresolvedStaleIn.data?.time),
									])
								}}
							</template>
						</span>
						<span class="g-banner__hint">
							<template v-if="isAbandoned">
								{{ __("Submit a late check-out now to resolve.") }}
							</template>
							<template v-else>
								{{ __("Tap to submit a late check-out for approval.") }}
							</template>
						</span>
					</div>
					<GBadge variant="open" class="shrink-0">{{ __("Resolve") }}</GBadge>
				</div>
			</GBanner>

			<GButton
				id="open-checkin-modal"
				class="mt-5"
				:label="nextAction.label"
				@click="handleEmployeeCheckin"
			>
				<template #trailing>
					<FeatherIcon name="arrow-right" class="w-[17px] h-[17px]" />
				</template>
			</GButton>
		</template>

		<div v-else class="text-card-title text-ink-600 mt-1">
			{{ dayjs().format("ddd, D MMMM, YYYY") }}
		</div>
	</div>

	<!-- The "Check in" screen of §12 is a bottom sheet here, not a route — see
	     the anatomy divergence note in the phase 5 HANDOFF. GModal carries the
	     focus-trap workaround (§16.3) the raw ion-modal did not. -->
	<GModal
		v-if="settings.data?.allow_employee_checkin_from_mobile_app"
		trigger="open-checkin-modal"
		@did-present="onModalPresent"
		@will-dismiss="onModalDismiss"
	>
		<div class="checkin-sheet__stack">
			<div class="flex flex-col gap-1">
				<div class="g-eyebrow">{{ nextAction.label }}</div>
				<!-- No :seconds. GClock renders seconds and suffix in the SAME
				     smaller style, so "02:56" + "44" + "pm" read as one broken
				     time — an operator filed "what is the 44, is that seconds?".
				     The component's own note calls the seconds decorative, and
				     decoration that reads as data is worse than none. Nothing
				     about a check-in needs second precision on screen; the
				     stored timestamp keeps it. -->
				<GClock
					:time="dayjs(checkinTimestamp).format('hh:mm')"
					:suffix="dayjs(checkinTimestamp).format('a')"
				/>
				<div class="text-caption text-ink-2">{{ dayjs().format("D MMM, YYYY") }}</div>
			</div>

			<template v-if="settings.data?.allow_geolocation_tracking">
				<div class="w-full flex flex-row items-center justify-between text-caption">
					<span class="text-ink-2">{{ locationStatus }}</span>
					<span
						v-if="shiftLocation.data && distanceToShift !== null"
						class="font-mono tabular-nums"
						:class="isInsideRadius ? 'text-accent-ink' : 'text-ink'"
					>
						{{ formattedDistanceToShift }}
					</span>
				</div>

				<!-- The real Leaflet map goes in GMapPanel's slot; the panel's
				     decorative gradient is only its placeholder state. -->
				<GMapPanel>
					<div ref="mapEl" class="checkin-sheet__map"></div>
				</GMapPanel>
			</template>

			<!-- Live selfie preview — camera auto-starts when the modal opens;
			     Confirm tap captures the frame, uploads, and submits the log
			     in one action (mirrors the React CheckInDialog UX). -->
			<GSelfiePanel :tappable="false" :label="__('Check-in photo preview')">
				<div class="checkin-sheet__camera">
					<video
						v-show="cameraStatus === 'live' || cameraStatus === 'submitting'"
						ref="videoEl"
						autoplay
						playsinline
						muted
						class="checkin-sheet__video"
					></video>
					<div v-if="cameraStatus === 'starting'" class="checkin-sheet__camera-msg">
						{{ __("Starting camera...") }}
					</div>
					<div v-else-if="cameraStatus === 'error'" class="checkin-sheet__camera-msg">
						<span>{{ cameraError }}</span>
					</div>
				</div>
			</GSelfiePanel>
			<canvas ref="canvasEl" class="hidden"></canvas>

			<GButton
				:label="__('Confirm {0}', [nextAction.label])"
				:disabled="cameraStatus === 'starting'"
				:pending="submitting || punchCheckin.loading || cameraStatus === 'submitting'"
				@click="submitLog(nextAction.action)"
			>
				<template #trailing>
					<FeatherIcon name="check" class="w-[17px] h-[17px]" />
				</template>
			</GButton>
		</div>
	</GModal>

	<RemoteCheckinDialog
		:is-open="remoteDialogOpen"
		:request-name="remoteRequest.name"
		:log-type="remoteRequest.logType"
		:distance-m="remoteRequest.distanceM"
		:approver-name="remoteRequest.approverName"
		:reason="remoteRequest.reason"
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
		:accuracy-m="strictRejection.accuracyM"
		@close="strictDialogOpen = false"
	/>

	<LateCheckoutDialog
		:is-open="lateCheckoutOpen"
		:in-checkin-name="unresolvedStaleIn.data?.name || ''"
		:in-checkin-time="unresolvedStaleIn.data?.time || ''"
		@close="lateCheckoutOpen = false"
		@submitted="
			() => {
				checkins.reload()
				unresolvedStaleIn.reload()
			}
		"
	/>
</template>

<script setup>
import GSelfiePanel from "@/components/glass/GSelfiePanel.vue"
import GMapPanel from "@/components/glass/GMapPanel.vue"
import GClock from "@/components/glass/GClock.vue"
import GModal from "@/components/glass/GModal.vue"
import GBadge from "@/components/glass/GBadge.vue"
import GBanner from "@/components/glass/GBanner.vue"
import GButton from "@/components/glass/GButton.vue"
import { createResource, createListResource, toast, FeatherIcon } from "frappe-ui"
import { computed, inject, nextTick, ref, onMounted, onBeforeUnmount, watch } from "vue"
import { modalController } from "@ionic/vue"

import L from "leaflet"
import "leaflet/dist/leaflet.css"
import markerIcon from "leaflet/dist/images/marker-icon.png"
import markerIcon2x from "leaflet/dist/images/marker-icon-2x.png"
import markerShadow from "leaflet/dist/images/marker-shadow.png"

import { formatTimestamp } from "@/utils/formatters"
import {
	GEO_DENIED,
	GEO_INSECURE,
	GEO_TIMEOUT,
	GEO_UNSUPPORTED,
	describeGeolocationError,
	formatAccuracy,
	geolocationBlockedReason,
} from "@/utils/geolocation"
import RemoteCheckinDialog from "@/components/RemoteCheckinDialog.vue"
import StrictRejectionDialog from "@/components/StrictRejectionDialog.vue"
import LateCheckoutDialog from "@/components/LateCheckoutDialog.vue"

// Bundled Leaflet cannot derive its default marker icon paths (it guesses them
// from where leaflet.css was served), so hand it the URLs Vite emits.
L.Icon.Default.mergeOptions({
	iconRetinaUrl: markerIcon2x,
	iconUrl: markerIcon,
	shadowUrl: markerShadow,
})

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
let geoWatchId = null
// Per-modal-session geolocation state. latitude/longitude refs persist across
// modal open/close, so "do we have a fix yet" must NOT be derived from them —
// both are reset in fetchLocation() each time the modal opens.
let hasSessionFix = false
let coarseFallbackRequested = false
// How sure the device was about the coordinates above, in metres. Sent with
// both the preflight and the punch: the fence is tens of metres wide and a
// phone indoors, an iPad on wifi and a desktop with no radio disagree about
// their own position by more than that. Without it the server has no way to
// tell a reading apart from a fact.
const accuracyM = ref(null)

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

// Staff lockdown: desk create perms on Employee Checkin are stripped, so the
// punch goes through a server-side endpoint (owner check + server clock).
const punchCheckin = createResource({
	url: "hrms.api.remote_checkin.punch",
})

// Remote checkin dialog state
const remoteDialogOpen = ref(false)
const remoteRequest = ref({
	name: "",
	logType: "IN",
	distanceM: 0,
	approverName: "",
	reason: "outside_radius",
})

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
	accuracyM: 0,
})

const preflightGeofence = createResource({
	url: "hrms.api.geofence.check_geofence",
	makeParams(values) {
		return values
	},
})

// Late-checkout dialog state. Server-resolved: the banner must survive the
// employee checking IN the next morning (which buries the stale IN below
// newer rows, so last-log inspection goes blind).
const lateCheckoutOpen = ref(false)
const unresolvedStaleIn = createResource({
	url: "hrms.api.remote_checkin.get_unresolved_stale_in",
	auto: true,
	onError() {
		console.warn("[CheckInPanel] Failed to fetch unresolved stale check-in")
	},
})
const hasStaleOpenIn = computed(() => !!unresolvedStaleIn.data?.name)
const isAbandoned = computed(() => !!unresolvedStaleIn.data?.is_abandoned)

const fetchRemoteRequest = createResource({
	url: "frappe.client.get_list",
	makeParams(values) {
		return {
			doctype: "Remote Checkin Request",
			filters: { checkin: values.checkin },
			fields: ["name", "log_type", "distance_m", "approver", "status"],
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
		console.info("[CheckInPanel] lastLog resolved:", {
			name: row.name,
			log_type: row.log_type,
			time: row.time,
			requires_remote_approval: row.requires_remote_approval,
			is_abandoned: row.is_abandoned,
		})
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
// §16.7 #2 — the button state derives from the employee's OPEN SHIFT, not the
// calendar date. The old rule expired an open IN at 6am the following day,
// which fires *during* a night shift: someone who punched in at 22:05 on a
// 22:00–07:00 shift was offered "Check In" at 06:30, still on shift, and again
// at 07:10 having simply forgotten to punch out — creating a second open IN
// either way. Reproduced before this change; see the phase 7 HANDOFF.
//
// A punch session stays open until it has run longer than any real shift, or
// until the server's nightly sweeper marks it abandoned — which is the
// authoritative "this session is over" signal and already drives the
// forgot-to-check-out banner above.
const MAX_OPEN_SHIFT_HOURS = 16

function isSessionStale(checkinTime) {
	if (!checkinTime) return true
	const t = new Date(checkinTime)
	if (Number.isNaN(t.getTime())) return true
	// the server has ruled on this session; the client does not second-guess it
	if (unresolvedStaleIn.data?.is_abandoned) return true
	return Date.now() - t.getTime() >= MAX_OPEN_SHIFT_HOURS * 60 * 60 * 1000
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
	accuracyM.value = position.coords.accuracy ?? null

	const parts = [
		__("Latitude: {0}°", [Number(latitude.value).toFixed(5)]),
		__("Longitude: {0}°", [Number(longitude.value).toFixed(5)]),
	]
	// Shown, not swallowed: when a check-in needs approving because the device
	// could only place it to within a kilometre, that number is the answer to
	// the question the employee is about to ask.
	const accuracy = formatAccuracy(accuracyM.value)
	if (accuracy) parts.push(__("Accuracy: {0}", [accuracy]))
	locationStatus.value = parts.join(", ")

	const firstFixThisSession = !hasSessionFix
	hasSessionFix = true
	updateUserMarker()
	// On reopen the marker already exists at last session's stale coords, so
	// the creation-time recenter doesn't fire — re-fit on this session's
	// first real fix instead.
	if (firstFixThisSession) fitMapBounds()
}

// What to tell someone whose device would not say where it is. The raw
// GeolocationPositionError used to be printed at them verbatim, which named
// no cause they could act on and differed per browser for the same failure.
function locationErrorMessage(code) {
	switch (code) {
		case GEO_DENIED:
			return __(
				"Location permission is off for this site. Turn it back on in your browser or device settings, then try again."
			)
		case GEO_TIMEOUT:
			return __(
				"Still looking for your location. Move near a window or wait a moment, then try again."
			)
		case GEO_INSECURE:
			return __(
				"This page is not on a secure (https) connection, so your browser will not share your location. Open the app from its https address."
			)
		case GEO_UNSUPPORTED:
			return __("Geolocation is not supported by your current browser")
		default:
			return __("Your device could not determine your location right now.")
	}
}

function handleLocationError(error) {
	const code = describeGeolocationError(error)
	locationStatus.value = locationErrorMessage(code)
	console.warn("[CheckInPanel] geolocation error:", code, error)

	// The high-accuracy watch gave up before any fix. This is not one
	// platform's problem: a handset indoors, an iPad with wifi scanning off
	// and a desk browser with no radio all land here. Grab one coarse
	// network-based position so the map still centers on the user instead of
	// staying on the fallback view — the reading arrives with its own accuracy
	// attached, and the server decides what a coarse one is worth. One attempt
	// per modal session (watch TIMEOUT recurs every ~15s), re-checked at
	// resolution so a slower coarse result never overwrites a real fix that
	// landed in the meantime.
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
	const blocked = geolocationBlockedReason()
	if (blocked) {
		locationStatus.value = locationErrorMessage(blocked)
		console.warn("[CheckInPanel] geolocation unavailable on this page:", blocked)
		return
	}
	locationStatus.value = __("Locating...")
	hasSessionFix = false
	coarseFallbackRequested = false
	accuracyM.value = null
	// watchPosition gives us live updates while the modal is open so the
	// user pin moves in real time as the device's GPS drifts/refines.
	if (geoWatchId !== null) {
		navigator.geolocation.clearWatch(geoWatchId)
	}
	// maximumAge 60s: a high-accuracy provider cold-starts slowly on every
	// platform, and with maximumAge 0 even a seconds-old cached fix is
	// rejected, so indoor users timed out with no pin at all. A recent cached
	// fix is fine for a check-in radius measured in tens of metres — and it
	// carries its own accuracy, so a stale-ish reading cannot pass itself off
	// as a sharp one.
	geoWatchId = navigator.geolocation.watchPosition(handleLocationSuccess, handleLocationError, {
		enableHighAccuracy: true,
		maximumAge: 60000,
		timeout: 15000,
	})
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
	if (!L) return null
	return L.latLng(loc.latitude, loc.longitude).distanceTo(
		L.latLng(latitude.value, longitude.value)
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
	// Leaflet is bundled, so it is present the moment this module is. The 5s
	// poll that used to sit here waited on a deferred CDN <script> that could
	// simply never arrive on a slow or filtered network — the map was blank or
	// silently skipped, and check-in evidence went with it.
	if (!mapEl.value || leafletMap) return

	const loc = shiftLocation.data
	const center = loc
		? [loc.latitude, loc.longitude]
		: latitude.value && longitude.value
		? [latitude.value, longitude.value]
		: [3.139, 101.6869] // KL fallback so the tile layer renders something
	const zoom = loc ? 16 : 13

	leafletMap = L.map(mapEl.value, {
		zoomControl: false,
		attributionControl: false,
		dragging: true,
		tap: true,
		// Android Chrome/WebView intermittently fails to composite the SVG
		// overlay pane inside the transformed modal container, leaving the
		// radius circle invisible; the canvas renderer is immune.
		preferCanvas: true,
	}).setView(center, zoom)

	L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
		maxZoom: 19,
	}).addTo(leafletMap)

	if (loc) {
		const shiftLatLng = L.latLng(loc.latitude, loc.longitude)
		shiftMarker = L.marker(shiftLatLng, {
			title: loc.label,
		}).addTo(leafletMap)
		shiftMarker.bindTooltip(loc.label || __("Shift Location"), {
			permanent: true,
			direction: "top",
			offset: [0, -28],
			className: "shift-loc-tooltip",
		})
		if (loc.checkin_radius > 0) {
			L.circle(shiftLatLng, {
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
	if (!leafletMap || !L) return
	if (!latitude.value || !longitude.value) return

	const here = L.latLng(latitude.value, longitude.value)
	if (!userMarker) {
		// Custom blue dot — Leaflet's default icon is a tall pin which reads
		// awkwardly for "this is you right now"; a dot is the convention.
		const dotIcon = L.divIcon({
			className: "user-pin",
			html: '<div class="user-pin-dot"></div><div class="user-pin-ring"></div>',
			iconSize: [22, 22],
			iconAnchor: [11, 11],
		})
		userMarker = L.marker(here, {
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
	if (!leafletMap || !L) return
	const points = []
	if (shiftMarker) points.push(shiftMarker.getLatLng())
	if (userMarker) points.push(userMarker.getLatLng())
	if (points.length === 2) {
		leafletMap.fitBounds(L.latLngBounds(points), {
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
}

// If the shift-location fetch finishes after the map is already up
// (slow network on first open), paint the pin + circle now.
watch(
	() => shiftLocation.data,
	(loc) => {
		if (!leafletMap || !L || !loc) return
		if (!shiftMarker) {
			const shiftLatLng = L.latLng(loc.latitude, loc.longitude)
			shiftMarker = L.marker(shiftLatLng).addTo(leafletMap)
			shiftMarker.bindTooltip(loc.label || __("Shift Location"), {
				permanent: true,
				direction: "top",
				offset: [0, -28],
				className: "shift-loc-tooltip",
			})
			if (loc.checkin_radius > 0) {
				L.circle(shiftLatLng, {
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

// §11.5 — a second submission of the same action within 60 seconds is rejected
// client-side. This is not cosmetic: the app has produced up to nine identical
// check-in records from one user in the same second. `submitting` is set
// SYNCHRONOUSLY, before the first await, because every await in this function
// is a window in which another tap lands.
const DUPLICATE_WINDOW_MS = 60 * 1000
const submitting = ref(false)
const lastSubmit = ref({ action: null, at: 0 })

const submitLog = async (logType) => {
	if (submitting.value) {
		console.info("[CheckInPanel] punch already in flight, ignoring tap")
		return
	}
	if (
		lastSubmit.value.action === logType &&
		Date.now() - lastSubmit.value.at < DUPLICATE_WINDOW_MS
	) {
		console.warn("[CheckInPanel] duplicate {0} within 60s, rejected".replace("{0}", logType))
		return
	}
	submitting.value = true
	try {
		await runSubmitLog(logType)
		lastSubmit.value = { action: logType, at: Date.now() }
	} finally {
		// released on every path — an early return from the geofence preflight
		// must not leave the button stuck pending
		submitting.value = false
	}
}

// The original body, unchanged. It is wrapped rather than edited because it has
// several early returns (strict geofence, remote fallback) and each one has to
// release the guard.
const runSubmitLog = async (logType) => {
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
				// Sent here as well as with the punch. The preview and the
				// insert must decide from identical inputs, or the screen
				// blocks a punch the server would have taken — the exact
				// drift the preflight exists to prevent.
				accuracy: accuracyM.value,
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
					accuracyM: Number(result.accuracy_m) || 0,
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

	// no `time` in the payload — the punch endpoint stamps the server clock
	const payload = {
		employee: employee.data.name,
		log_type: logType,
		latitude: latitude.value,
		longitude: longitude.value,
		accuracy: accuracyM.value,
	}
	if (selfieUrl) {
		payload.selfie_image = selfieUrl
	}

	punchCheckin.submit(payload, {
		async onSuccess(doc) {
			modalController.dismiss()

			// Refresh the log list so lastLog (and the stale "Forgot to check out"
			// banner / button state) reflect the log just inserted. The socket
			// list_update handler also reloads, but it's unreliable on mobile
			// (disconnected/backgrounded), so reload explicitly like the dialogs do.
			checkins.reload()
			unresolvedStaleIn.reload()

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
							// From the punch response, not the request row: the
							// row records the distance, not whether the distance
							// could be trusted in the first place.
							reason: doc.remote_reason || "outside_radius",
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
							text: __("A prior remote check-in request today was rejected — please contact HR."),
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
			unresolvedStaleIn.reload()
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
/* ---- check-in sheet layout (phase 5 batch 2) ---- */
.checkin-sheet__stack {
	display: flex;
	flex-direction: column;
	gap: var(--g-stack-md);
	width: 100%;
}
/* the Leaflet canvas fills GMapPanel's frame; §10.2 #19 sets that at 150px */
.checkin-sheet__map {
	position: absolute;
	inset: 0;
	z-index: 0;
}
.checkin-sheet__camera {
	position: relative;
	width: 100%;
	aspect-ratio: 4 / 3;
	background: var(--g-ink);
}
.checkin-sheet__video {
	width: 100%;
	height: 100%;
	object-fit: cover;
	transform: scaleX(-1);
}
.checkin-sheet__camera-msg {
	position: absolute;
	inset: 0;
	display: flex;
	align-items: center;
	justify-content: center;
	padding: 0 var(--g-screen-gutter);
	text-align: center;
	font-family: var(--g-type-caption-family);
	font-size: var(--g-type-caption-size);
	color: var(--g-bg);
}

/* Live "you are here" pin — solid blue dot with a pulsing outer ring. */
.user-pin {
	position: relative;
	width: 22px;
	height: 22px;
}
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
	0% {
		transform: scale(0.8);
		opacity: 0.9;
	}
	100% {
		transform: scale(2.2);
		opacity: 0;
	}
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
.shift-loc-tooltip:before {
	display: none !important;
}

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
