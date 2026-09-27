// alpha.14 A (owner screenshot, 27 Sep 2026): a check-in opened from
// Check-ins showed "Employee Checkin", raw Latitude / Longitude rows, a map
// and the photo as a file name. Owner: the coordinate is a must but quiet —
// it is there to trace a problem — and every attachment shows a preview.
// The words come from the stored outcome (employee_checkin_override.py
// sets geofence_outcome on every punch); a number never appears without its
// unit, a missing reading never as 0 or NaN.
import { test } from "node:test"
import assert from "node:assert/strict"
import { whereLine, coordinateLine } from "../checkinSheet.js"

test("inside the area, with how far from its centre", () => {
	assert.equal(whereLine({ geofence_outcome: "Inside", geofence_distance_m: 40.4 }), "Inside the work area · 40 m")
})

test("outside says how far, in km past a kilometre", () => {
	assert.equal(whereLine({ geofence_outcome: "Outside", geofence_distance_m: 820 }), "Outside the work area · 820 m")
	assert.equal(whereLine({ geofence_outcome: "Outside", geofence_distance_m: 12400 }), "Outside the work area · 12.4 km")
})

test("every other outcome in plain words, without a distance", () => {
	const words = {
		Imprecise: "Location too rough to place",
		"Free Location": "Anywhere allowed",
		"No Shift": "No shift that day",
		"No Location": "No work area set",
		"No Radius": "No work area set",
		"Tracking Off": "Location was off",
		"Late Checkout": "Added later (forgot to check out)",
		"Manual Entry": "Added by HR",
	}
	for (const [outcome, line] of Object.entries(words)) assert.equal(whereLine({ geofence_outcome: outcome, geofence_distance_m: 5 }), line, outcome)
})

test("an older punch with no outcome shows nothing rather than a guess", () => {
	assert.equal(whereLine({}), "")
})

test("coordinates: five decimals, only for a real reading", () => {
	assert.equal(coordinateLine({ latitude: 3.174372, longitude: 101.685431 }), "3.17437, 101.68543")
	assert.equal(coordinateLine({ latitude: 0, longitude: 0 }), "")
	assert.equal(coordinateLine({ latitude: null, longitude: 101.6 }), "")
	assert.equal(coordinateLine({}), "")
})

test("a coarse reading never shows a confident distance (same rule as the check-in dialog)", () => {
	assert.equal(whereLine({ geofence_outcome: "Outside", geofence_distance_m: 820, location_accuracy_m: 900 }), "Outside the work area")
	assert.equal(whereLine({ geofence_outcome: "Inside", geofence_distance_m: 40, location_accuracy_m: 12 }), "Inside the work area · 40 m")
})

import { readFileSync } from "node:fs"
import { fileURLToPath } from "node:url"
const read = (p) => readFileSync(fileURLToPath(new URL(p, import.meta.url)), "utf8")

test("Check-ins opens this sheet, not the generic request sheet with raw fields", () => {
	const list = read("../../components/ListView.vue")
	assert.match(list, /<CheckinSheet v-if="selectedRequest" :punch="selectedRequest" \/>/)
	assert.doesNotMatch(list, /formatted_latitude|formatted_longitude/)
	const fields = read("../../views/attendance/EmployeeCheckinList.vue")
	for (const f of ["geofence_outcome", "geofence_distance_m", "location_accuracy_m", "selfie_image"]) assert.match(fields, new RegExp(`"${f}"`), f)
})

test("the sheet shows the photo, the place in words, and the coordinates quietly", () => {
	const sheet = read("../../components/CheckinSheet.vue")
	assert.match(sheet, /<img[\s\S]*:src="punch\.selfie_image"/)
	assert.match(sheet, /whereLine\(props\.punch\)/)
	assert.match(sheet, /class="g-form-footer g-checkin-sheet__coords/)
	// what renders (the <template>, comments dropped): no raw field names, no map
	const template = sheet.slice(sheet.indexOf("<template>"), sheet.indexOf("</template>\n\n<script")).replace(/<!--[\s\S]*?-->/g, "")
	assert.doesNotMatch(template, /Employee Checkin|[Ll]atitude|[Ll]ongitude|<GMapPanel/)
})
