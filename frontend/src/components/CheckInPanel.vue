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
				interactive
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

			<!-- A written verdict, not a map.
			     HR asked for the map to go, and it was the wrong instrument
			     anyway. It answered "where am I?", which the employee already
			     knows, and never answered the two things they cannot work out:
			     am I close enough, and what happens if I am not. The old caption
			     read "120 m from office" — a bare fact, with the radius unstated
			     and the consequence unmentioned.
			     It also fetched tiles from tile.openstreetmap.org, so on a
			     filtered network or a weak signal the one piece of UI meant to
			     reassure people rendered blank. -->
			<div v-if="settings.data?.allow_geolocation_tracking" class="checkin-sheet__where">
				<div class="checkin-sheet__where-title" :class="`is-${locationVerdict.tone}`">
					{{ locationVerdict.title }}
				</div>
				<div class="checkin-sheet__where-detail">{{ locationVerdict.detail }}</div>
			</div>

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
import GClock from "@/components/glass/GClock.vue"
import GModal from "@/components/glass/GModal.vue"
import GBadge from "@/components/glass/GBadge.vue"
import GBanner from "@/components/glass/GBanner.vue"
import GButton from "@/components/glass/GButton.vue"
import { createResource, createListResource, toast, FeatherIcon } from "frappe-ui"
import { computed, inject, nextTick, ref, onBeforeUnmount } from "vue"
import { useListUpdate } from "@/composables/realtime"
import { modalController } from "@ionic/vue"

import { formatTimestamp } from "@/utils/formatters"
import {
	GEO_DENIED,
	GEO_INSECURE,
	GEO_TIMEOUT,
	GEO_UNSUPPORTED,
	describeGeolocationError,
	formatAccuracy,
	geolocationBlockedReason,
	preferFreshFix,
	shouldReplaceFix,
	usablePosition,
	validCoordinates,
	MAX_FIX_AGE_MS,
	previewGeofence,
} from "@/utils/geolocation"
import RemoteCheckinDialog from "@/components/RemoteCheckinDialog.vue"
import StrictRejectionDialog from "@/components/StrictRejectionDialog.vue"
import LateCheckoutDialog from "@/components/LateCheckoutDialog.vue"

const DOCTYPE = "Employee Checkin"

const socket = inject("$socket")
const employee = inject("$employee")
const dayjs = inject("$dayjs")
const __ = inject("$translate")
const checkinTimestamp = ref(null)
const latitude = ref(null)
const longitude = ref(null)
const locationStatus = ref("")
// Separate from locationStatus because the two answer different questions.
// locationStatus carried BOTH "Latitude: 3.13901, Longitude: 101.68690" and
// "Location permission denied", so nothing downstream could tell a reading from
// a failure. The verdict below has to.
const locationError = ref("")

let geoWatchId = null
let geoGeneration = 0
let sheetSession = 0
let fixExpiryTimer = null
// A browser that accepts the location request and then never calls back —
// neither success nor error. Reported from mainland China on 10 Sep 2026: a new
// phone, a browser whose location bridge never answered, and a panel that said
// "Finding your location..." until the employee gave up. The watch timeout and
// the coarse retry are the BROWSER's promises to us, so neither fires when the
// browser is the thing that is broken. This is our own deadline.
let locationDeadlineTimer = null
const locationStalled = ref(false)
// Answering with readings we discard is not the same fault as never answering,
// and it is not the same advice: a different browser helps the silent one, only
// open sky helps the one whose fixes are unusable.
// A ref, not a plain flag: the verdict is a computed, and a reading that
// arrives AFTER the deadline has already fired must still correct the wording.
const sawGeolocationCallback = ref(false)
const LOCATION_DEADLINE_MS = 30000
// Per-modal-session geolocation state. latitude/longitude refs persist across
// modal open/close, so "do we have a fix yet" must NOT be derived from them —
// both are reset in fetchLocation() each time the modal opens.
let hasSessionFix = false
let coarseFallbackRequested = false
// Timestamp of the fix we're currently holding. watchPosition's first reading can
// be a cached one up to maximumAge old (60s): if it happens to be sharp, the
// sharpest-fix rule would keep it and reject every fresher live reading, pinning a
// user who has since moved at their old spot. A reading this much newer wins on
// freshness even if marginally less accurate.
let fixTimestamp = null
const STALE_FIX_MS = 30000
// How sure the device was about the coordinates above, in metres. Sent with
// both the preflight and the punch: the fence is tens of metres wide and a
// phone indoors, an iPad on wifi and a desktop with no radio disagree about
// their own position by more than that. Without it the server has no way to
// tell a reading apart from a fact.
const accuracyM = ref(null)

const activeShiftLocation = ref(null)
const shiftLocationState = ref("loading")
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
let cameraGeneration = 0
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

function isSessionStale(log) {
	const checkinTime = log?.time
	if (!checkinTime) return true
	// Frappe datetimes are "YYYY-MM-DD HH:mm:ss" (space, no T). Safari — iOS
	// especially — parses that as Invalid Date, which made every open IN look
	// stale: the button flipped to "Check In" and check-out created a SECOND
	// open session. Normalise the space to a T so every browser parses it as
	// local time (unchanged behaviour where new Date already worked).
	const t = new Date(String(checkinTime).replace(" ", "T"))
	if (Number.isNaN(t.getTime())) return true
	// The server has ruled on THIS session; the client does not second-guess it.
	// Matched by name on purpose: the banner points at the newest IN already
	// past its 06:00 cutoff — never today's fresh check-in. Applying that row's
	// abandoned flag to whatever happened to be the newest log left anyone with
	// one forgotten check-out stuck on "Check In" forever, however recently
	// they had just checked in.
	if (unresolvedStaleIn.data?.is_abandoned && unresolvedStaleIn.data?.name === log?.name) {
		return true
	}
	return Date.now() - t.getTime() >= MAX_OPEN_SHIFT_HOURS * 60 * 60 * 1000
}

const liveAction = computed(() => {
	const last = lastLog?.value
	if (!last || last.log_type !== "IN" || isSessionStale(last)) {
		return { action: "IN", label: __("Check In") }
	}
	return { action: "OUT", label: __("Check Out") }
})

// The action the open sheet committed to. Taken ONCE when the sheet presents
// and held until it dismisses, because liveAction recomputes whenever the log
// reloads — a socket list_update, a pull-to-refresh, the post-punch reload —
// and lastLog is `{}` while that reload is in flight, which resolves to "IN".
// So the sheet could say "Check Out", the list could refresh underneath it, and
// Confirm would submit an IN. That is how a day ends up with two INs and no
// OUT: zero working hours, a Half Day, and on anyone who also holds a night
// shift the evening punch lands on the 7PM shift and splits the day in two.
// The server refuses to take the type on trust either (resolve_punch_type);
// this removes the trigger, that removes the consequence.
const committedAction = ref(null)
const nextAction = computed(() => committedAction.value || liveAction.value)

function handleLocationSuccess(position, generation) {
	if (generation !== geoGeneration) return
	sawGeolocationCallback.value = true
	const fix = usablePosition(position, Date.now())
	if (!fix) return
	const acc = fix.accuracy
	const readingAt = fix.timestamp
	if (hasSessionFix && readingAt < fixTimestamp) return
	// Keep the SHARPEST fix over the modal's short, stationary window, not merely
	// the latest: watchPosition streams readings as GPS refines AND drifts, and a
	// later, worse reading must not overwrite a good one and place a present user
	// outside their own office (the 102 m-from-Damansara report).
	// Exception: a reading much fresher than the one we hold takes it regardless of
	// accuracy — otherwise a stale-but-sharp cached first fix sticks (see fixTimestamp).
	const muchFresher = hasSessionFix && preferFreshFix(fixTimestamp, readingAt, STALE_FIX_MS)
	if (!muchFresher && !shouldReplaceFix(accuracyM.value, acc, hasSessionFix)) return
	console.info("[CheckInPanel] location fix updated, accuracy(m):", acc)
	latitude.value = fix.latitude
	longitude.value = fix.longitude
	accuracyM.value = acc
	fixTimestamp = readingAt
	clearTimeout(locationDeadlineTimer)
	locationDeadlineTimer = null
	locationStalled.value = false
	clearTimeout(fixExpiryTimer)
	fixExpiryTimer = setTimeout(() => {
		if (generation !== geoGeneration || fixTimestamp !== readingAt) return
		clearLocationFix()
		locationError.value = __(
			"Your location reading expired. Wait for a fresh reading, then try again."
		)
	}, MAX_FIX_AGE_MS - (Date.now() - readingAt) + 1)

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
	locationError.value = ""

	hasSessionFix = true
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

function handleLocationError(error, generation) {
	if (generation !== geoGeneration) return
	sawGeolocationCallback.value = true
	// The browser has explained itself, which beats the deadline's guess even
	// when the deadline fired first — a slow POSITION_UNAVAILABLE is still the
	// better answer.
	locationStalled.value = false
	const code = describeGeolocationError(error)
	if (code === GEO_DENIED) stopWatchingLocation()
	locationStatus.value = locationErrorMessage(code)
	locationError.value = locationStatus.value
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
	if (code !== GEO_DENIED && !hasSessionFix && !coarseFallbackRequested && navigator.geolocation) {
		coarseFallbackRequested = true
		navigator.geolocation.getCurrentPosition(
			(position) => {
				if (generation === geoGeneration && !hasSessionFix)
					handleLocationSuccess(position, generation)
			},
			() => {},
			{ enableHighAccuracy: false, maximumAge: MAX_FIX_AGE_MS, timeout: 10000 }
		)
	}
}

const fetchLocation = () => {
	stopWatchingLocation()
	const generation = geoGeneration
	const blocked = geolocationBlockedReason()
	if (blocked) {
		locationStatus.value = locationErrorMessage(blocked)
		locationError.value = locationStatus.value
		console.warn("[CheckInPanel] geolocation unavailable on this page:", blocked)
		return
	}
	locationStatus.value = __("Locating...")
	locationError.value = ""
	locationStalled.value = false
	sawGeolocationCallback.value = false
	clearTimeout(locationDeadlineTimer)
	locationDeadlineTimer = setTimeout(() => {
		// A real error already explains itself, and a fix makes the question
		// moot — this speaks only into the silence.
		if (generation !== geoGeneration || hasSessionFix || locationError.value) return
		locationStalled.value = true
		console.warn("[CheckInPanel] no geolocation callback in %d ms", LOCATION_DEADLINE_MS)
	}, LOCATION_DEADLINE_MS)
	hasSessionFix = false
	coarseFallbackRequested = false
	accuracyM.value = null
	fixTimestamp = null
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
	geoWatchId = navigator.geolocation.watchPosition(
		(position) => handleLocationSuccess(position, generation),
		(error) => handleLocationError(error, generation),
		{
			enableHighAccuracy: true,
			maximumAge: MAX_FIX_AGE_MS,
			timeout: 15000,
		}
	)
}

function clearLocationFix() {
	console.info("[CheckInPanel] clearing held location")
	clearTimeout(fixExpiryTimer)
	fixExpiryTimer = null
	hasSessionFix = false
	latitude.value = longitude.value = null
	accuracyM.value = fixTimestamp = null
	locationStatus.value = locationError.value = ""
}

function stopWatchingLocation() {
	geoGeneration += 1
	coarseFallbackRequested = false
	clearTimeout(locationDeadlineTimer)
	locationDeadlineTimer = null
	locationStalled.value = false
	sawGeolocationCallback.value = false
	activeShiftLocation.value = null
	shiftLocationState.value = "loading"
	clearLocationFix()
	if (geoWatchId !== null && navigator.geolocation) {
		navigator.geolocation.clearWatch(geoWatchId)
		geoWatchId = null
	}
}

// ---------------------------------------------------------------------------
// Leaflet map — shift location pin + radius circle + live user pin
// Distance to the shift location, and the written verdict built from it.

// Metres between two coordinates. Was L.latLng().distanceTo(), which is the
// only reason Leaflet was a dependency of this app at all — 150 KB of mapping
// library for one number, plus a runtime fetch to tile.openstreetmap.org that
// silently rendered nothing on a filtered network.
//
// Haversine on a spherical earth. Good to ~0.3% against WGS84, which over a
// check-in radius measured in tens of metres is centimetres — far below the
// device's own error, and that error is already carried explicitly as accuracyM.
function metresBetween(lat1, lon1, lat2, lon2) {
	const R = 6371008.8 // IUGG mean earth radius
	const toRad = (deg) => (deg * Math.PI) / 180
	const dLat = toRad(lat2 - lat1)
	const dLon = toRad(lon2 - lon1)
	const a =
		Math.sin(dLat / 2) ** 2 +
		Math.cos(toRad(lat1)) * Math.cos(toRad(lat2)) * Math.sin(dLon / 2) ** 2
	return 2 * R * Math.asin(Math.min(1, Math.sqrt(a)))
}

const distanceToShift = computed(() => {
	const loc = activeShiftLocation.value
	if (
		!loc ||
		!validCoordinates(loc.latitude, loc.longitude) ||
		!validCoordinates(latitude.value, longitude.value)
	)
		return null
	return metresBetween(loc.latitude, loc.longitude, latitude.value, longitude.value)
})

const fencePreview = computed(() => {
	const loc = activeShiftLocation.value
	return previewGeofence({
		strict: loc?.strict,
		hasLocation: !!loc && loc.has_shift_location !== false,
		radius: loc?.checkin_radius,
		distance: distanceToShift.value,
		accuracy: accuracyM.value,
		freeLocation: !!loc?.free_location,
	})
})

// What the employee needs, in the order they need it: the VERDICT, then the
// number, then what happens next. The old caption gave only the number —
// "120 m from office" — which is unreadable without the radius and says nothing
// about the consequence. Staff had no way to know that an out-of-range punch is
// accepted and routed for approval rather than lost.
//
// Check-OUT is judged the same as check-in: HR requires clock-in and clock-out to
// be in the same assigned area. The server already enforced this on the insert;
// the screen used to say the opposite ("recorded as-is"), which is the mismatch
// this removes. How strict that enforcement is stays the shift's own setting.
const locationVerdict = computed(() => {
	if (locationStalled.value) {
		// Blocked, not muted: with geolocation tracking on, the server refuses a
		// punch that carries no coordinates, so this employee genuinely cannot
		// clock in until the reading arrives. Name the browser — it is the one
		// thing standing here that they can actually change.
		return sawGeolocationCallback.value
			? {
					tone: "blocked",
					title: __("Your device cannot fix your location"),
					detail: __(
						"It is answering, but none of the readings are usable. Step outside or next to a window, then reopen this screen."
					),
			  }
			: {
					tone: "blocked",
					title: __("Your browser is not sharing a location"),
					detail: __(
						"It has not answered for {0} seconds. Try a different browser, or step outside and reopen this screen.",
						[Math.round(LOCATION_DEADLINE_MS / 1000)]
					),
			  }
	}
	if (locationError.value) {
		// Severity follows the coordinates, not the error object. With tracking
		// on, no coordinates means the server will refuse the punch — so a
		// browser that answers PERMISSION_DENIED after a silent stall must not
		// make this banner RELAX at the moment the punch became impossible.
		//
		// The muted arm is the ordinary indoor case, not an edge: a live watch
		// re-issues TIMEOUT every ~15s while a perfectly good fix is still
		// held, and that punch will be accepted. Fix EXPIRY is the other way
		// round — it clears the coordinates first, so it reads blocked.
		return {
			tone: validCoordinates(latitude.value, longitude.value) ? "muted" : "blocked",
			title: __("Location unavailable"),
			detail: locationError.value,
		}
	}

	if (shiftLocationState.value !== "ready") {
		return {
			tone: "muted",
			title:
				shiftLocationState.value === "error"
					? __("Could not load your assigned area")
					: __("Checking your assigned area..."),
			detail: __("Your check-in will be checked by the server when you submit."),
		}
	}

	const loc = activeShiftLocation.value
	if (loc?.free_location) {
		// Sales staff and anyone without a fixed workplace. HR marked the Shift
		// Location free, so there is no fence: the punch is recorded wherever
		// they are and never goes to an approver. Said before any distance maths
		// so a blank coordinate set is never reported as "needs setup".
		return {
			tone: "ok",
			title: __("Free location"),
			detail: __(
				"You're not tied to one workplace. Your check-in is recorded wherever you are, with no approval needed."
			),
		}
	}

	if (!loc || loc.has_shift_location === false) {
		// Not an error and not the employee's problem, so it is stated plainly
		// rather than warned about. Silence here was its own bug: the panel
		// showed a map of nothing and the employee assumed they were being
		// checked when nobody was checking.
		return {
			tone: loc?.strict ? "blocked" : "muted",
			title: __("No check-in area set for your shift"),
			detail: loc?.strict
				? __("Ask HR to configure the check-in area before you submit.")
				: __("Your location will not be checked. Tell HR if that looks wrong."),
		}
	}

	if (!(loc.checkin_radius > 0) || !validCoordinates(loc.latitude, loc.longitude)) {
		return {
			tone: loc.strict ? "blocked" : "muted",
			title: __("Check-in area needs setup"),
			detail: __("Ask HR to check the area's coordinates and radius."),
		}
	}

	const d = distanceToShift.value
	if (d === null) {
		return {
			tone: "muted",
			title: __("Finding your location..."),
			detail: __("Just a moment."),
		}
	}

	const away = d >= 1000 ? __("{0} km", [(d / 1000).toFixed(1)]) : __("{0} m", [Math.round(d)])
	const radius = __("{0} m", [loc.checkin_radius])

	// Check-out is range-checked exactly like check-in now — HR requires clock-in
	// and clock-out to be in the same assigned area — so the verdict below speaks
	// for both. `verb` keeps each sentence correct for whichever action is next;
	// the degree of enforcement (block vs record-and-flag) is the shift's own
	// strict/lenient setting, identical for both directions.
	const verb = nextAction.value?.action === "OUT" ? __("check out") : __("check in")

	if (fencePreview.value.action === "allow") {
		// The accuracy grace already exists server-side — evaluate_geofence
		// widens the radius by the device's own error estimate. Saying so turns
		// "why did it accept me, I'm clearly outside" into an explained decision.
		const slack = accuracyM.value
		const wide = slack && d > loc.checkin_radius
		return {
			tone: "ok",
			title: __("You're at {0}", [loc.label]),
			detail: wide
				? __("Your GPS reading is a little rough, but you're close enough — go ahead and {0}.", [
						verb,
				  ])
				: __("You're within range. Go ahead and {0}.", [verb]),
		}
	}

	if (fencePreview.value.reason === "imprecise_location") {
		return {
			tone: loc.strict ? "blocked" : "warn",
			title: __("Your location is uncertain"),
			detail: loc.strict
				? __(
						"Your device cannot place you accurately enough. Wait for a better reading, then try again."
				  )
				: __("Your device cannot place you accurately enough. Your check-in will need approval."),
		}
	}

	if (loc.strict) {
		return {
			tone: "blocked",
			title: __("Too far from {0}", [loc.label]),
			detail: __("You need to be within {0} of {1} to {2}. Move closer and try again.", [
				radius,
				loc.label,
				verb,
			]),
		}
	}

	return {
		tone: "warn",
		title: __("{0} from {1}", [away, loc.label]),
		detail: __(
			"You're outside the {0} range. You can still {1} — it'll be sent to your approver to approve.",
			[radius, verb]
		),
	}
})

const handleEmployeeCheckin = async () => {
	sheetSession += 1
	checkinTimestamp.value = dayjs().format("YYYY-MM-DD HH:mm:ss")
	if (!settings.data?.allow_geolocation_tracking) {
		stopWatchingLocation()
		return
	}
	fetchLocation()
	const generation = geoGeneration
	try {
		const location = await shiftLocation.reload()
		if (generation !== geoGeneration) return
		activeShiftLocation.value = location
		shiftLocationState.value = "ready"
	} catch (error) {
		if (generation === geoGeneration) shiftLocationState.value = "error"
		console.warn("[CheckInPanel] assigned area could not be loaded", error)
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
	const generation = geoGeneration
	try {
		// Arm the duplicate guard ONLY on a successful punch. The old code armed
		// it right after a fire-and-forget submit, so a punch that later FAILED
		// still locked the user out of retrying the same action for 60s.
		const ok = await runSubmitLog(logType)
		if (ok) lastSubmit.value = { action: logType, at: Date.now() }
		if (!ok && generation === geoGeneration && cameraStatus.value === "submitting") {
			cameraStatus.value = "idle"
			startCamera()
		}
	} catch (err) {
		// A rejected punch is already surfaced to the user by onError (toast +
		// camera reset); swallow here so it is not an unhandled rejection, and
		// leave lastSubmit un-armed so retry is allowed. Belt-and-suspenders
		// camera reset in case onError did not run.
		console.error("[CheckInPanel] submit failed:", err)
		if (generation === geoGeneration && cameraStatus.value === "submitting") {
			cameraStatus.value = "idle"
			startCamera()
		}
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
	const session = sheetSession
	const generation = geoGeneration
	const tracking = settings.data?.allow_geolocation_tracking
	const fix = tracking
		? usablePosition(
				{
					coords: {
						latitude: latitude.value,
						longitude: longitude.value,
						accuracy: accuracyM.value,
					},
					timestamp: fixTimestamp,
				},
				Date.now()
		  )
		: null
	const location = Object.freeze({ ...fix, generation })
	const locationStillUsable = () =>
		generation === geoGeneration &&
		(!tracking ||
			(!geolocationBlockedReason() &&
				usablePosition({ coords: location, timestamp: location.timestamp }, Date.now())))
	const requireLocation = () => {
		if (locationStillUsable()) return true
		if (generation === geoGeneration) {
			console.warn("[CheckInPanel] punch needs a current location reading")
			if (cameraStatus.value === "submitting") {
				cameraStatus.value = "idle"
				startCamera()
			}
			handleEmployeeCheckin()
			toast({
				title: __("Location needed"),
				text: __("Wait for a fresh location reading, then try again."),
				icon: "map-pin",
			})
		}
		return false
	}
	if (!requireLocation()) return false
	const actionLabel = logType === "IN" ? __("Check-in") : __("Check-out")

	// Preflight strict geofence: if the assigned Shift Type has
	// enable_strict_geofence and we're outside the radius (or the shift is
	// misconfigured), the server-side validate will throw. Catch this here
	// so the user sees the explanatory dialog instead of a generic toast.
	if (tracking) {
		try {
			const result = await preflightGeofence.submit({
				employee: employee.data.name,
				log_type: logType,
				latitude: location.latitude,
				longitude: location.longitude,
				// Sent here as well as with the punch. The preview and the
				// insert must decide from identical inputs, or the screen
				// blocks a punch the server would have taken — the exact
				// drift the preflight exists to prevent.
				accuracy: location.accuracy,
			})
			if (!requireLocation()) return false
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
				// not a success — leave the duplicate guard un-armed so the user
				// can retry the moment they move inside the radius.
				return false
			}
		} catch (err) {
			// Preflight is advisory — if it fails, fall through and let the
			// real insert path enforce policy. Avoid blocking the user on a
			// transient network blip.
			console.warn("[Preflight] check_geofence failed, falling through:", err)
		}
	}

	if (!requireLocation()) return false

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
			// Free only the camera belonging to this submission.
			if (generation === geoGeneration) stopCamera()
		}
	}

	if (!requireLocation()) return false

	// no `time` in the payload — the punch endpoint stamps the server clock
	const payload = {
		employee: employee.data.name,
		log_type: logType,
		latitude: location.latitude ?? null,
		longitude: location.longitude ?? null,
		accuracy: location.accuracy ?? null,
	}
	if (selfieUrl) {
		payload.selfie_image = selfieUrl
	}

	let punchOk = false
	await punchCheckin.submit(payload, {
		async onSuccess(doc) {
			punchOk = true

			// Refresh the log list so lastLog (and the stale "Forgot to check out"
			// banner / button state) reflect the log just inserted. The socket
			// list_update handler also reloads, but it's unreliable on mobile
			// (disconnected/backgrounded), so reload explicitly like the dialogs do.
			checkins.reload()
			unresolvedStaleIn.reload()
			if (generation !== geoGeneration) return
			modalController.dismiss()

			if (doc?.requires_remote_approval) {
				try {
					const rows = await fetchRemoteRequest.submit({ checkin: doc.name })
					if (session !== sheetSession) return
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
			// A failed punch used to leave cameraStatus stuck at "submitting" —
			// the Confirm button a permanent, un-tappable spinner over a dead
			// black camera — and, when the error carried no message, showed
			// nothing at all. Free the button, bring the camera back so the user
			// can retry with a fresh selfie, and always say something.
			if (generation === geoGeneration && cameraStatus.value === "submitting") {
				cameraStatus.value = "idle"
				startCamera()
			}
			const messages = error?.messages?.length
				? error.messages
				: [__("{0} failed. Check your connection and try again.", [actionLabel])]
			for (const message of messages) {
				toast({
					title: __("Error"),
					text: message,
					icon: "alert-circle",
					position: "bottom-center",
					iconClasses: "text-red-500",
				})
			}
		},
	})
	return punchOk
}

async function startCamera() {
	stopCamera()
	const generation = cameraGeneration
	cameraError.value = null
	cameraStatus.value = "starting"
	if (!navigator.mediaDevices?.getUserMedia) {
		cameraError.value = __("Camera not supported on this device")
		cameraStatus.value = "error"
		return
	}
	try {
		const stream = await navigator.mediaDevices.getUserMedia({
			video: {
				facingMode: "user",
				width: { ideal: 640 },
				height: { ideal: 480 },
			},
		})
		if (generation !== cameraGeneration) {
			stream.getTracks().forEach((track) => track.stop())
			return
		}
		cameraStream = stream
		cameraStatus.value = "live"
		await nextTick()
		if (generation !== cameraGeneration) return
		if (videoEl.value) {
			videoEl.value.srcObject = cameraStream
		}
		console.info("[Selfie] Camera started")
	} catch (err) {
		if (generation !== cameraGeneration) return
		console.error("[Selfie] Camera error:", err)
		cameraError.value = __("Camera access denied. Please allow camera permission.")
		cameraStatus.value = "error"
	}
}

function stopCamera() {
	cameraGeneration += 1
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
	// Commit to one action for the life of this sheet. What the user reads on
	// the way in is what Confirm submits, whatever the log does underneath.
	committedAction.value = liveAction.value
	console.info("[CheckInPanel] sheet committed to:", committedAction.value.action)
	// Auto-start the camera as soon as the check-in sheet is fully open.
	startCamera()
}

function onModalDismiss() {
	committedAction.value = null
	stopCamera()
	cameraStatus.value = "idle"
	cameraError.value = null
	stopWatchingLocation()
}

// Realtime: reload on Employee Checkin changes. Via useListUpdate so the
// handler is detached BY REFERENCE on unmount — a bare socket.off("list_update")
// tore down every OTHER component's list_update listener too — and is rejoined
// on reconnect.
useListUpdate(socket, DOCTYPE, () => {
	checkins.reload()
	unresolvedStaleIn.reload()
})

onBeforeUnmount(() => {
	sheetSession += 1
	stopCamera()
	stopWatchingLocation()
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
/* The written location verdict that replaced the map. Tone is carried by
   colour AND by the wording, never colour alone — the verdict has to survive a
   greyscale screenshot and a colour-blind reader. */
.checkin-sheet__where {
	display: flex;
	flex-direction: column;
	gap: 2px;
}
.checkin-sheet__where-title {
	font: var(--g-type-card-title);
	color: var(--g-ink);
}
.checkin-sheet__where-title.is-ok {
	color: var(--g-accent-ink);
}
.checkin-sheet__where-title.is-warn,
.checkin-sheet__where-title.is-blocked {
	color: var(--g-warn-ink, var(--g-ink));
}
.checkin-sheet__where-detail {
	font: var(--g-type-caption);
	color: var(--g-ink-2);
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
