// Compile the actual SFC setup; Vue refs/computeds are real. Browser location,
// camera and network resources are explicit boundaries, with controlled callbacks.
import assert from "node:assert/strict"
import { test } from "node:test"
import { readFileSync } from "node:fs"
import { compileScript, parse } from "@vue/compiler-sfc"
import { computed, nextTick, reactive, ref } from "vue"
import * as geolocation from "../../utils/geolocation.js"

const source = readFileSync(new URL("../CheckInPanel.vue", import.meta.url), "utf8")
const script = compileScript(parse(source).descriptor, { id: "checkin-location" })
const code = script.content
	.replace(/import[\s\S]*?from ["'][^"']+["'];?/g, "")
	.replace("export default", "return")

function panel() {
	let now = 1_800_000_000_000
	const watches = [],
		coarse = [],
		requests = [],
		notices = [],
		unmount = []
	const counters = { dismiss: 0, reload: 0 }
	const resources = new Map()
	const upload = { respond: null }
	const timers = new Map()
	let timerId = 0
	const navigator = {
		geolocation: {
			watchPosition(success, error, options) {
				watches.push({ success, error, options })
				return watches.length
			},
			clearWatch() {},
			getCurrentPosition(success, error, options) {
				coarse.push({ success, error, options })
			},
		},
	}
	const window = { navigator, isSecureContext: true, location: { hostname: "example.invalid" } }
	const createResource = (options) => {
		const resource = reactive({
			data: null,
			reload: async () => resource.data,
			submit: async (params) => {
				requests.push({ url: options.url, params })
				return null
			},
		})
		if (options.url === "hrms.api.get_hr_settings")
			resource.data = { allow_geolocation_tracking: true }
		if (options.url === "hrms.api.geofence.get_active_shift_location")
			resource.data = {
				latitude: 3,
				longitude: 101.5,
				checkin_radius: 100,
				label: "Office",
				strict: false,
			}
		resources.set(options.url, resource)
		return resource
	}
	const dayjs = () => ({ format: () => "2027-01-15 08:00:00" })
	const bindings = {
		fetch: async (url) =>
			url.startsWith("data:")
				? { blob: async () => new Blob([]) }
				: new Promise((resolve) => {
						upload.respond = resolve
				  }),
		...geolocation,
		ref,
		computed,
		nextTick,
		createResource,
		geolocationBlockedReason: () => geolocation.geolocationBlockedReason(window),
		createListResource: () => ({
			data: [],
			list: {},
			reload: async () => {
				counters.reload += 1
			},
		}),
		inject: (name) =>
			({
				$employee: { data: { name: "EMP" } },
				$translate: (text) => text,
				$dayjs: dayjs,
				$socket: {},
			}[name]),
		onBeforeUnmount: (fn) => unmount.push(fn),
		useListUpdate: () => {},
		modalController: {
			dismiss: async () => {
				counters.dismiss += 1
			},
		},
		toast: (notice) => notices.push(notice),
		formatTimestamp: () => "",
		window,
		navigator,
		Date: class extends Date {
			static now() {
				return now
			}
		},
		setTimeout: (fn, delay) => {
			timers.set(++timerId, { fn, at: now + delay })
			return timerId
		},
		clearTimeout: (id) => timers.delete(id),
		console: { info() {}, warn() {}, error() {} },
	}
	for (const name of Object.keys(script.imports)) if (!(name in bindings)) bindings[name] = {}
	const component = new Function(...Object.keys(bindings), code)(...Object.values(bindings))
	const vm = component.setup({}, { expose() {} })
	const fix = (latitude = 3, longitude = 101.5, accuracy = 20, timestamp = now) => ({
		coords: { latitude, longitude, accuracy },
		timestamp,
	})
	return {
		vm,
		counters,
		upload,
		watches,
		coarse,
		requests,
		notices,
		window,
		resources,
		fix,
		unmount: () => unmount.forEach((fn) => fn()),
		advance: (ms) => {
			now += ms
			for (const [id, timer] of timers)
				if (timer.at <= now) {
					timers.delete(id)
					timer.fn()
				}
		},
	}
}

test("closing and reopening clears the previous session coordinates before any callback", () => {
	const h = panel()
	h.vm.handleEmployeeCheckin()
	h.watches[0].success(h.fix())
	h.vm.onModalDismiss()
	assert.equal(h.vm.latitude.value, null)
	assert.equal(h.vm.longitude.value, null)
	h.vm.handleEmployeeCheckin()
	assert.equal(h.vm.distanceToShift.value, null)
})

test("a blocked reopen clears coordinates and late callbacks cannot restore them", () => {
	const h = panel()
	h.vm.handleEmployeeCheckin()
	h.watches[0].success(h.fix())
	h.window.isSecureContext = false
	h.vm.handleEmployeeCheckin()
	h.watches[0].success(h.fix(4, 102))
	assert.equal(h.vm.latitude.value, null)
	assert.equal(h.vm.longitude.value, null)
	assert.equal(h.vm.distanceToShift.value, null)
})

test("obsolete watch and coarse callbacks cannot write into a reopened or unmounted sheet", () => {
	const h = panel()
	h.vm.handleEmployeeCheckin()
	h.watches[0].error({ code: 3 })
	assert.equal(h.coarse.length, 1)
	h.vm.onModalDismiss()
	h.vm.handleEmployeeCheckin()
	h.coarse[0].success(h.fix(4, 102))
	assert.equal(h.vm.latitude.value, null)
	h.watches[1].success(h.fix())
	h.watches[0].error({ code: 1 })
	assert.equal(h.vm.latitude.value, 3)
	h.unmount()
	h.watches[1].success(h.fix(4, 102))
	assert.equal(h.vm.latitude.value, null)
})

test("invalid or stale device fixes never become usable coordinates", () => {
	for (const fix of [
		{ coords: { latitude: NaN, longitude: 101.5, accuracy: 20 }, timestamp: 1_800_000_000_000 },
		{ coords: { latitude: 91, longitude: 101.5, accuracy: 20 }, timestamp: 1_800_000_000_000 },
		{ coords: { latitude: 3, longitude: 181, accuracy: 20 }, timestamp: 1_800_000_000_000 },
		{ coords: { latitude: 3, longitude: 101.5, accuracy: -1 }, timestamp: 1_800_000_000_000 },
		{
			coords: { latitude: 3, longitude: 101.5, accuracy: Infinity },
			timestamp: 1_800_000_000_000,
		},
		{ coords: { latitude: 3, longitude: 101.5, accuracy: 20 }, timestamp: 1_800_000_060_000 },
		{ coords: { latitude: 3, longitude: 101.5, accuracy: 20 }, timestamp: 1_799_999_699_999 },
	]) {
		const h = panel()
		h.vm.handleEmployeeCheckin()
		h.watches[0].success(fix)
		assert.equal(h.vm.latitude.value, null, JSON.stringify(fix))
	}
})

test("zero coordinates are a valid fix and receive preflight and punch together", async () => {
	const h = panel()
	await h.vm.handleEmployeeCheckin()
	h.watches[0].success(h.fix(0, 0))
	assert.notEqual(h.vm.distanceToShift.value, null)
	await h.vm.submitLog("IN")
	assert.equal(h.requests[0].url, "hrms.api.geofence.check_geofence")
	assert.equal(h.requests[0].params.latitude, 0)
	assert.equal(h.requests[1].params.longitude, 0)
})

test("stale current coordinates never enter an actual punch payload", async () => {
	const h = panel()
	h.vm.handleEmployeeCheckin()
	h.watches[0].success(h.fix())
	h.advance(61_000)
	await h.vm.submitLog("IN")
	assert.equal(h.requests.length, 0)
	assert.equal(h.vm.latitude.value, null)
	assert.ok(h.notices.length)
})

test("the sheet stops displaying an expired fix even before another tap", async () => {
	const h = panel()
	await h.vm.handleEmployeeCheckin()
	h.watches[0].success(h.fix())
	assert.equal(h.vm.distanceToShift.value, 0)
	h.advance(60_001)
	assert.equal(h.vm.distanceToShift.value, null)
	assert.ok(h.vm.locationError.value)
	assert.equal(
		h.vm.locationVerdict.value.detail,
		"Your location reading expired. Wait for a fresh reading, then try again."
	)
})

test("preflight and punch use the same selected snapshot when a newer fix arrives", async () => {
	const h = panel()
	h.vm.handleEmployeeCheckin()
	h.watches[0].success(h.fix())
	let finish
	const params = []
	h.resources.get("hrms.api.geofence.check_geofence").submit = async (value) => {
		params.push(value)
		await new Promise((resolve) => {
			finish = resolve
		})
		return { ok: true }
	}
	const submit = h.vm.submitLog("IN")
	h.advance(1000)
	h.watches[0].success(h.fix(4, 102, 10))
	finish()
	await submit
	const punch = h.requests.find((row) => row.url === "hrms.api.remote_checkin.punch")
	assert.equal(punch.params.latitude, params[0].latitude)
	assert.equal(punch.params.longitude, params[0].longitude)
	assert.equal(punch.params.accuracy, params[0].accuracy)
})

test("a preflight finishing after expiry or a close cannot send a punch", async () => {
	for (const action of ["expire", "close", "reopen", "denied"]) {
		const h = panel()
		h.vm.handleEmployeeCheckin()
		h.watches[0].success(h.fix())
		let finish
		h.resources.get("hrms.api.geofence.check_geofence").submit = async () => {
			await new Promise((resolve) => {
				finish = resolve
			})
			return { ok: true }
		}
		const submit = h.vm.submitLog("IN")
		if (action === "expire") h.advance(61_000)
		else if (action === "denied") h.watches[0].error({ code: 1 })
		else {
			h.vm.onModalDismiss()
			if (action === "reopen") h.vm.handleEmployeeCheckin()
		}
		finish()
		await submit
		assert.equal(h.requests.length, 0, action)
		assert.equal(h.vm.submitting.value, false)
		assert.equal(h.vm.lastSubmit.value.action, null)
	}
})

test("an old area response cannot replace the reopened sheet's assigned area", async () => {
	const h = panel()
	const resource = h.resources.get("hrms.api.geofence.get_active_shift_location")
	const finish = []
	resource.reload = () =>
		new Promise((resolve) =>
			finish.push((data) => {
				resource.data = data
				resolve(data)
			})
		)
	const oldOpen = h.vm.handleEmployeeCheckin()
	h.vm.onModalDismiss()
	const newOpen = h.vm.handleEmployeeCheckin()
	h.watches[1].success(h.fix())
	const current = {
		latitude: 3,
		longitude: 101.5,
		checkin_radius: 100,
		label: "Current",
		strict: false,
	}
	finish[1](current)
	await newOpen
	assert.equal(h.vm.distanceToShift.value, 0)
	finish[0]({ ...current, latitude: 4, label: "Old" })
	await oldOpen
	assert.equal(h.vm.distanceToShift.value, 0)
})

test("the written preview respects accuracy allowance and distinguishes uncertainty from distance", async () => {
	for (const [distance, accuracy, tone, title] of [
		[120, 40, "ok", "You're at {0}"],
		[1300, 1500, "warn", "Your location is uncertain"],
		[10, 1500, "ok", "You're at {0}"],
		[10, 5000, "warn", "Your location is uncertain"],
	]) {
		const h = panel()
		await h.vm.handleEmployeeCheckin()
		// A northward meridian offset; expected boundary cases come from HR's examples.
		h.watches[0].success(h.fix(3 + ((distance / 6371008.8) * 180) / Math.PI, 101.5, accuracy))
		assert.equal(h.vm.locationVerdict.value.tone, tone, `${distance}/${accuracy}`)
		assert.equal(h.vm.locationVerdict.value.title, title, `${distance}/${accuracy}`)
	}
})

test("a selfie upload outliving the fix aborts the punch and releases the camera button", async () => {
	const h = panel()
	await h.vm.handleEmployeeCheckin()
	h.watches[0].success(h.fix())
	h.vm.cameraStatus.value = "live"
	h.vm.videoEl.value = { videoWidth: 640, videoHeight: 480 }
	h.vm.canvasEl.value = {
		getContext: () => ({ translate() {}, scale() {}, drawImage() {}, setTransform() {} }),
		toDataURL: () => "data:image/jpeg;base64,",
	}
	const submit = h.vm.submitLog("IN")
	await new Promise(setImmediate)
	assert.equal(typeof h.upload.respond, "function")
	h.advance(61_000)
	h.upload.respond({
		ok: true,
		json: async () => ({ message: { file_url: "/files/selfie.jpg" } }),
	})
	await submit
	assert.equal(h.requests.filter((row) => row.url === "hrms.api.remote_checkin.punch").length, 0)
	assert.notEqual(h.vm.cameraStatus.value, "submitting")
	assert.equal(h.vm.submitting.value, false)
	assert.equal(h.vm.lastSubmit.value.action, null)
})

test("an old upload cannot stop the camera belonging to a reopened sheet", async () => {
	const h = panel()
	const stops = [0, 0]
	let camera = 0
	h.window.navigator.mediaDevices = {
		getUserMedia: async () => {
			const id = camera++
			return {
				getTracks: () => [
					{
						stop: () => {
							stops[id] += 1
						},
					},
				],
			}
		},
	}
	await h.vm.handleEmployeeCheckin()
	h.vm.onModalPresent()
	await new Promise(setImmediate)
	h.watches[0].success(h.fix())
	h.vm.videoEl.value = { videoWidth: 640, videoHeight: 480 }
	h.vm.canvasEl.value = {
		getContext: () => ({ translate() {}, scale() {}, drawImage() {}, setTransform() {} }),
		toDataURL: () => "data:image/jpeg;base64,",
	}
	const submit = h.vm.submitLog("IN")
	await new Promise(setImmediate)
	h.vm.onModalDismiss()
	await h.vm.handleEmployeeCheckin()
	h.vm.onModalPresent()
	await new Promise(setImmediate)
	h.upload.respond({
		ok: true,
		json: async () => ({ message: { file_url: "/files/selfie.jpg" } }),
	})
	await submit
	assert.deepEqual(stops, [1, 0])
	assert.equal(h.vm.cameraStatus.value, "live")
})

test("an old successful POST refreshes confirmed punches without dismissing a newer sheet", async () => {
	const h = panel()
	await h.vm.handleEmployeeCheckin()
	h.watches[0].success(h.fix())
	let finish
	h.resources.get("hrms.api.remote_checkin.punch").submit = async (_payload, options) => {
		await new Promise((resolve) => {
			finish = resolve
		})
		await options.onSuccess({ name: "PUNCH-CONFIRMED" })
	}
	const submit = h.vm.submitLog("IN")
	await new Promise(setImmediate)
	h.vm.onModalDismiss()
	await h.vm.handleEmployeeCheckin()
	finish()
	await submit
	assert.equal(h.counters.dismiss, 0)
	assert.equal(h.counters.reload, 2)
	assert.equal(h.vm.lastSubmit.value.action, "IN")
})

test("generated session histories never revive a closed, denied or expired location", async () => {
	for (let seed = 1; seed <= 32; seed++) {
		const h = panel()
		let random = seed,
			active = -1,
			expected = null
		for (let step = 0; step < 80; step++) {
			random = (Math.imul(random, 1664525) + 1013904223) >>> 0
			switch (random % 7) {
				case 0:
					await h.vm.handleEmployeeCheckin()
					active = h.watches.length - 1
					expected = null
					break
				case 1:
					h.vm.onModalDismiss()
					active = -1
					expected = null
					break
				case 2:
					if (active >= 0) {
						expected = seed
						h.watches[active].success(h.fix(seed, 100))
					}
					break
				case 3: {
					const obsolete = h.watches.findIndex((_watch, index) => index !== active)
					if (obsolete >= 0) h.watches[obsolete].success(h.fix(-40, 100))
					break
				}
				case 4:
					h.advance(61000)
					expected = null
					break
				case 5:
					if (active >= 0) {
						h.watches[active].error({ code: 1 })
						active = -1
						expected = null
					}
					break
				case 6:
					h.window.isSecureContext = false
					await h.vm.handleEmployeeCheckin()
					h.window.isSecureContext = true
					active = -1
					expected = null
					break
			}
			assert.equal(h.vm.latitude.value, expected, `seed=${seed} step=${step}`)
		}
		h.unmount()
	}
})

test("sharper wins until a genuinely fresher fix replaces it, and older sharp callbacks cannot rewind it", async () => {
	const h = panel()
	await h.vm.handleEmployeeCheckin()
	h.watches[0].success(h.fix(3, 101.5, 5))
	h.advance(1000)
	h.watches[0].success(h.fix(4, 101.5, 50))
	assert.equal(h.vm.latitude.value, 3)
	h.advance(31_000)
	h.watches[0].success(h.fix(4, 101.5, 50))
	assert.equal(h.vm.latitude.value, 4)
	h.watches[0].success(h.fix(5, 101.5, 1, 1_800_000_000_000))
	assert.equal(h.vm.latitude.value, 4)
})

test("a camera permission result from a closed sheet is stopped instead of attaching to its replacement", async () => {
	const h = panel()
	const finish = [],
		stops = [0, 0]
	h.window.navigator.mediaDevices = {
		getUserMedia: () => new Promise((resolve) => finish.push(resolve)),
	}
	await h.vm.handleEmployeeCheckin()
	h.vm.onModalPresent()
	h.vm.onModalDismiss()
	await h.vm.handleEmployeeCheckin()
	h.vm.onModalPresent()
	finish[1]({
		getTracks: () => [
			{
				stop: () => {
					stops[1] += 1
				},
			},
		],
	})
	await new Promise(setImmediate)
	finish[0]({
		getTracks: () => [
			{
				stop: () => {
					stops[0] += 1
				},
			},
		],
	})
	await new Promise(setImmediate)
	assert.deepEqual(stops, [1, 0])
	assert.equal(h.vm.cameraStatus.value, "live")
	h.unmount()
	assert.deepEqual(stops, [1, 1])
})

// Mainland China, 10 September: a new phone on a browser that accepted the
// location request and then never called back — not success, not error. The
// panel said "Finding your location... Just a moment." and kept saying it.
// The employee could not clock in, and nothing on screen suggested what to do.
//
// The 15-second watch timeout and the coarse retry are the browser's promises
// to us, and this browser did not keep either. So the panel needs a deadline
// of its own: after it, say plainly that the browser is not answering and what
// to try. A spinner is not an answer.
test("a browser that never calls back stops pretending it is still looking", () => {
	const h = panel()
	h.vm.handleEmployeeCheckin()
	const waiting = h.vm.locationVerdict.value
	assert.notEqual(waiting.tone, "blocked", "the sheet should open in a waiting state")

	h.advance(31_000) // no success, no error — the browser simply never answered

	assert.notEqual(
		h.vm.locationVerdict.value.title,
		"Finding your location...",
		"the panel is still claiming to look for a location a browser will never send"
	)
	assert.equal(h.vm.locationVerdict.value.tone, "blocked")
	assert.match(
		h.vm.locationVerdict.value.detail,
		/browser/i,
		"the message must point at the browser — that is the thing the employee can change"
	)
})

test("a fix that arrives before the deadline cancels it", () => {
	const h = panel()
	h.vm.handleEmployeeCheckin()
	h.watches[0].success(h.fix())
	h.advance(31_000)
	assert.notEqual(
		h.vm.locationVerdict.value.tone,
		"blocked",
		"the deadline fired over a location the browser had already given us"
	)
})

test("the deadline of a closed sheet cannot fire into the next one", () => {
	const h = panel()
	h.vm.handleEmployeeCheckin()
	h.vm.onModalDismiss()
	h.vm.handleEmployeeCheckin()
	h.watches[1].success(h.fix())
	h.advance(31_000)
	assert.notEqual(h.vm.locationVerdict.value.tone, "blocked")
})

test("a browser that answers with a real error is left to say so itself", () => {
	const h = panel()
	h.vm.handleEmployeeCheckin()
	h.watches[0].error({ code: 1 }) // permission denied — a definite answer
	const denied = h.vm.locationVerdict.value.title
	h.advance(31_000)
	assert.equal(
		h.vm.locationVerdict.value.title,
		denied,
		"the deadline overwrote a real browser error with a vaguer one"
	)
})

// Review of the deadline commit: two ways the message can be false.
test("a real error arriving after the deadline replaces the deadline's guess", () => {
	const h = panel()
	h.vm.handleEmployeeCheckin()
	h.advance(31_000)
	assert.equal(h.vm.locationVerdict.value.tone, "blocked")

	h.watches[0].error({ code: 2 }) // POSITION_UNAVAILABLE, 40s in

	assert.match(
		h.vm.locationVerdict.value.detail,
		/could not determine your location/i,
		"the browser finally explained itself and the panel kept guessing over it"
	)
})

test("a browser sending unusable readings is not accused of silence", () => {
	const h = panel()
	h.vm.handleEmployeeCheckin()
	// answering, but every reading is junk: usablePosition discards each one
	h.watches[0].success({ coords: { latitude: NaN, longitude: 101.5, accuracy: 20 }, timestamp: 0 })
	h.advance(31_000)

	assert.equal(h.vm.locationVerdict.value.tone, "blocked")
	assert.doesNotMatch(
		h.vm.locationVerdict.value.detail,
		/has not answered/i,
		"it did answer — it answered with readings we cannot use, which is different advice"
	)
})

test("a junk reading arriving after the deadline still corrects the wording", () => {
	const h = panel()
	h.vm.handleEmployeeCheckin()
	h.advance(31_000)
	assert.match(h.vm.locationVerdict.value.detail, /has not answered/i)

	// the browser was not silent after all, just useless
	h.watches[0].success({ coords: { latitude: NaN, longitude: 101.5, accuracy: 20 }, timestamp: 0 })

	assert.doesNotMatch(
		h.vm.locationVerdict.value.detail,
		/has not answered/i,
		"the flag is not reactive, so the verdict never recomputed"
	)
})
