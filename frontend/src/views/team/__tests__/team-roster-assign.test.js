// Team roster "Assign" (30 Sep 2026). The sheet's button rendered as an empty
// lime pill: GButton draws its text from the `label` prop and has no default
// slot, so the words written between its tags were thrown away (owner's
// screenshot). And a Shift Supervisor rosters their own shifts too, so their
// own row reads "You".
import { test } from "node:test"
import assert from "node:assert/strict"
import { readFileSync } from "node:fs"
import { fileURLToPath } from "node:url"
import { compileScript, parse } from "@vue/compiler-sfc"
import dayjs from "dayjs"
import { computed, reactive, ref } from "vue"

const read = (p) => readFileSync(fileURLToPath(new URL(p, import.meta.url)), "utf8")
const view = read("../TeamRoster.vue")
const button = read("../../../components/glass/GButton.vue")

test("GButton takes its text from label, not a default slot", () => {
	assert.match(button, /pending \? pendingLabel \|\| label : label/)
	assert.doesNotMatch(button, /<slot\s*\/>/, "no default slot to put words in")
})

test("the Assign shift button has words", () => {
	const tag = view.slice(view.indexOf("<GButton"), view.indexOf("/>", view.indexOf("<GButton")))
	assert.match(tag, /:label="__\('Assign shift'\)"/)
})

test("a supervisor's own row reads You", () => {
	assert.match(view, /member\.is_self \? __\("You"\) : member\.employee_name/)
})

// 2 Oct 2026: a supervisor changes and removes their team's shifts from Nadi.
const data = read("../../../data/team.js")

test("each day in the strip is a button that opens that day", () => {
	assert.match(
		view,
		/<button[\s\S]*?v-for="day in weekDays"[\s\S]*?@click="openDay\(member, day\)"/
	)
})

test("the day sheet has Change and Remove, wired to the roster endpoints", () => {
	assert.match(view, /:label="__\('Change shift'\)"/)
	assert.match(view, /:label="__\('Remove this day'\)"/)
	assert.match(data, /url: "hrms\.api\.roster\.change_shift_day"/)
	assert.match(data, /url: "hrms\.api\.roster\.remove_shift_day"/)
})

// HR, 2 Oct 2026: supervisors set the Day Type in Nadi too
test("assign and change both offer the day type and send it", () => {
	assert.equal(view.match(/:options="dayTypeOptions"/g).length, 2)
	assert.match(view, /day_type: form\.day_type,/)
	assert.match(view, /day_type: dayForm\.day_type,/)
	assert.match(view, /\{ label: __\("Follows the calendar"\), value: "None" \}/)
})

test("a day type change alone wakes Change shift", () => {
	assert.match(view, /dayForm\.day_type !== \(shift\.day_type \|\| "None"\)/)
	assert.match(view, /:disabled="!dayChanged"/)
})

test("the day cell marks a set day type", () => {
	assert.match(view, /"Public Holiday": "PH"/)
	assert.match(view, /v-if="dayTypeMark\(member, day\)"/)
})

test("a screen reader hears the day type too", () => {
	const fn = view.slice(view.indexOf("function dayLabel"), view.indexOf("function openDay"))
	assert.match(fn, /dayTypeOptions\.value\.find/)
})

// HR, 6 Oct 2026: "kalau aku letak off day macam tu je tak boleh save, kena ada
// shift". Assign enables on a shift OR a day type, and with no shift the day
// type is saved as a marker (set_day_type), never as a shift. These tests run
// the real component setup (HelpdeskHub.test.js recipe): the server resources,
// the toast and translation are the boundaries.
const script = compileScript(parse(view).descriptor, { id: "team-roster-assign" })
const setupCode = script.content
	// only line-start imports: the lazy `import("...")` of the refresher stays
	.replace(/^import\s[^;]*?from\s+["'][^"']+["'];?/gm, "")
	.replace("export default", "return")

const MEMBER = { name: "HR-EMP-0001", company: "Verifica", employee_name: "Aina" }

function sheet() {
	const calls = { assign: [], dayType: [], change: [], toasts: [] }
	const resource = (log) => ({
		loading: false,
		submit: (params, hooks) => log.push({ params, hooks }),
	})
	const translate = (text, args) => (args ? text.replace(/\{(\d+)\}/g, (_, i) => args[i]) : text)
	const bindings = {
		computed,
		reactive,
		ref,
		inject: (key) => (key === "$dayjs" ? dayjs : translate),
		onMounted: () => {},
		defineAsyncComponent: () => ({}),
		gToast: (options) => calls.toasts.push(options),
		teamRoster: { loading: false, data: null, submit() {}, reload() {} },
		teamManagers: { data: [], reload() {} },
		assignShift: resource(calls.assign),
		setDayType: resource(calls.dayType),
		changeShiftDay: resource(calls.change),
		removeShiftDay: resource([]),
		console: { info() {}, warn() {}, error() {} },
	}
	for (const name of Object.keys(script.imports)) if (!(name in bindings)) bindings[name] = {}
	const component = new Function(...Object.keys(bindings), setupCode)(...Object.values(bindings))
	const vm = component.setup({}, { expose() {} })
	vm.openAssign(MEMBER)
	return { vm, calls }
}

test("Assign is enabled with a day type and no shift", () => {
	const { vm } = sheet()
	vm.form.start_date = "2026-10-08"
	vm.form.day_type = "Off Day"
	assert.ok(vm.canSubmit.value)
})

test("Assign stays disabled with neither a shift nor a day type", () => {
	const { vm } = sheet()
	vm.form.start_date = "2026-10-08"
	assert.equal(vm.form.day_type, "None")
	assert.ok(!vm.canSubmit.value)
	vm.form.day_type = ""
	assert.ok(!vm.canSubmit.value, "an empty day type counts as none")
})

test("Assign stays disabled with no start date", () => {
	const { vm } = sheet()
	vm.form.start_date = ""
	vm.form.day_type = "Off Day"
	assert.ok(!vm.canSubmit.value)
})

test("Work day alone (no shift) cannot be saved: a day with no shift is never a work day", () => {
	const { vm } = sheet()
	vm.form.start_date = "2026-10-08"
	vm.form.day_type = "Work Day"
	assert.equal(vm.canSubmit.value, false)
	vm.form.shift_type = "Morning"
	assert.equal(vm.canSubmit.value, true, "Work day stays a Day type on a shift")
})

test("a day type alone saves a day marker and does not assign a shift", () => {
	const { vm, calls } = sheet()
	vm.form.start_date = "2026-10-08"
	vm.form.end_date = "2026-10-10"
	vm.form.day_type = "Off Day"
	vm.form.shift_location = "Lot 5" // a marker has no location: it must be ignored
	vm.submitAssign()
	assert.equal(calls.assign.length, 0, "insert_shift must not be called")
	assert.equal(calls.dayType.length, 1)
	assert.deepEqual(calls.dayType[0].params, {
		employee: "HR-EMP-0001",
		from_date: "2026-10-08",
		to_date: "2026-10-10",
		day_type: "Off Day",
	})
})

test("a one-day marker with no end date sends to_date null", () => {
	const { vm, calls } = sheet()
	vm.form.start_date = "2026-10-08"
	vm.form.end_date = ""
	vm.form.day_type = "Rest Day"
	vm.submitAssign()
	assert.equal(calls.dayType[0].params.to_date, null)
})

test("the marker toast says what was saved, in plain words", () => {
	const saved = (day_type, from, to) => {
		const { vm, calls } = sheet()
		vm.form.start_date = from
		vm.form.end_date = to
		vm.form.day_type = day_type
		vm.submitAssign()
		calls.dayType[0].hooks.onSuccess({ saved: 1 })
		assert.equal(vm.assignOpen.value, false, "the sheet closes")
		return calls.toasts[0]
	}
	assert.deepEqual(saved("Off Day", "2026-10-08", "2026-10-08"), {
		title: "Off day saved for 8 Oct",
		variant: "success",
	})
	assert.equal(saved("Off Day", "2026-10-08", "2026-10-10").title, "Off day saved for 8–10 Oct")
	assert.equal(saved("Off Day", "2026-10-08", "").title, "Off day saved for 8 Oct")
	assert.equal(saved("Rest Day", "2026-10-08", "2026-10-08").title, "Rest day saved for 8 Oct")
	assert.equal(
		saved("Public Holiday", "2026-10-08", "2026-10-08").title,
		"Public holiday saved for 8 Oct"
	)
	assert.equal(
		saved("Off Day", "2026-09-30", "2026-10-02").title,
		"Off day saved for 30 Sep – 2 Oct",
		"a range over a month end names both months"
	)
})

test("a refused marker shows the server's words", () => {
	const { vm, calls } = sheet()
	vm.form.start_date = "2026-10-08"
	vm.form.day_type = "Off Day"
	vm.submitAssign()
	calls.dayType[0].hooks.onError({ messages: ["This day already has punches."] })
	assert.deepEqual(calls.toasts[0], { title: "This day already has punches.", variant: "error" })
	calls.dayType[0].hooks.onError({})
	assert.equal(calls.toasts[1].variant, "error")
	assert.ok(calls.toasts[1].title, "a plain fallback when the server sends no words")
})

test("a shift still assigns through insert_shift exactly as before", () => {
	const { vm, calls } = sheet()
	vm.form.shift_type = "Morning"
	vm.form.shift_location = "Lot 5"
	vm.form.day_type = "Off Day"
	vm.form.start_date = "2026-10-08"
	vm.form.end_date = "2026-10-10"
	vm.submitAssign()
	assert.equal(calls.dayType.length, 0, "no marker call when a shift is picked")
	assert.equal(calls.assign.length, 1)
	assert.deepEqual(calls.assign[0].params, {
		employee: "HR-EMP-0001",
		company: "Verifica",
		shift_type: "Morning",
		start_date: "2026-10-08",
		end_date: "2026-10-10",
		status: "Active",
		shift_location: "Lot 5",
		day_type: "Off Day",
	})
	calls.assign[0].hooks.onSuccess({})
	assert.deepEqual(calls.toasts[0], { title: "Shift assigned", variant: "success" })
})

test("a shift with the default day type still assigns", () => {
	const { vm, calls } = sheet()
	vm.form.shift_type = "Morning"
	vm.form.start_date = "2026-10-08"
	assert.ok(vm.canSubmit.value)
	vm.submitAssign()
	assert.equal(calls.assign.length, 1)
	assert.equal(calls.assign[0].params.day_type, "None")
	assert.equal(calls.assign[0].params.shift_location, null)
})

test("submitting a disabled sheet sends nothing", () => {
	const { vm, calls } = sheet()
	vm.form.start_date = "2026-10-08"
	vm.submitAssign()
	assert.equal(calls.assign.length + calls.dayType.length, 0)
})

test("with a shift but no From date, the hint still shows and Save points at it", () => {
	const { vm } = sheet()
	vm.form.shift_type = "Morning"
	vm.form.start_date = ""
	assert.equal(vm.shiftHint.value, "Pick a From date.")
	assert.match(view, /v-if="!form\.shift_type \|\| !canSubmit"\s+id="assign-shift-hint"/)
	const tag = view.slice(view.indexOf("<GButton"), view.indexOf("/>", view.indexOf("<GButton")))
	assert.match(tag, /:aria-describedby="canSubmit \? undefined : 'assign-shift-hint'"/)
})

test("each grey-Save reason with no shift names itself", () => {
	const { vm } = sheet()
	vm.form.start_date = "2026-10-08"
	vm.form.day_type = "None"
	assert.match(vm.shiftHint.value, /^Leave empty and pick a Day type/)
	vm.form.day_type = "Work Day"
	assert.match(vm.shiftHint.value, /^Pick a shift, or choose/)
})

test("with no shift and no From date, the hint asks for the date", () => {
	const { vm } = sheet()
	vm.form.start_date = ""
	vm.form.day_type = "Off Day"
	assert.equal(vm.shiftHint.value, "Pick a From date.")
})

test("with no shift, a blocked Save says why and points at the reason", () => {
	const { vm } = sheet()
	vm.form.start_date = "2026-10-08"
	vm.form.day_type = "Work Day"
	assert.equal(vm.shiftHint.value, "Pick a shift, or choose Off day, Rest day or Public holiday.")
	vm.form.day_type = "Off Day"
	assert.equal(
		vm.shiftHint.value,
		"Leave empty and pick a Day type to mark the day only (Off, Rest, Public holiday)."
	)
	const tag = view.slice(view.indexOf("<GButton"), view.indexOf("/>", view.indexOf("<GButton")))
	assert.match(tag, /:aria-describedby="canSubmit \? undefined : 'assign-shift-hint'"/)
})

test("the Shift type hint shows only with no shift and is tied to the field", () => {
	const hint = view.match(/<span[^>]*id="assign-shift-hint"[^>]*>[\s\S]*?<\/span>/)?.[0]
	assert.ok(hint, "a hint line with an id")
	assert.match(hint, /v-if="!form\.shift_type \|\| !canSubmit"/)
	assert.match(hint, /\{\{ shiftHint \}\}/)
	// the field names the hint only while the hint is on screen
	assert.match(view, /:describedby="form\.shift_type && canSubmit \? '' : 'assign-shift-hint'"/)
	// and Link hands that id to the real picker button as aria-describedby
	const link = read("../../../components/Link.vue")
	assert.match(link, /:aria-describedby="describedby \|\| undefined"/)
})

test("Location shows only with a shift: a day marker has no location", () => {
	const field = view.slice(
		view.lastIndexOf("<label", view.indexOf('doctype="Shift Location"')),
		view.indexOf('doctype="Shift Location"')
	)
	assert.match(field, /v-if="form\.shift_type"/)
})

test("the Assign button stays a real disabled button and waits on both writes", () => {
	const tag = view.slice(view.indexOf("<GButton"), view.indexOf("/>", view.indexOf("<GButton")))
	assert.match(tag, /:disabled="!canSubmit"/)
	assert.match(tag, /assignShift\.loading \|\| setDayType\.loading/)
})

test("set_day_type is wired through the roster fence", () => {
	assert.match(
		data,
		/export const setDayType = createResource\(\{\s*url: "hrms\.api\.roster\.set_day_type"/
	)
	assert.match(view, /import \{[^}]*\bsetDayType\b[^}]*\} from "@\/data\/team"/)
})

// Owner, R3a, 7 Oct 2026: the Day sheet edits the day's location too. The server keeps what is
// not sent, so submitChange sends shift_location ONLY when it changed; an emptied field sends ""
// (clears it). get_team_roster already carries shift_location on each shift row (team.py).
const DAY = { iso: "2026-10-08" }
const dayOf = (shift) => ({
	...MEMBER,
	shifts: [
		{
			name: "HR-SHA-0001",
			shift_type: "Morning",
			shift_location: "Lot 5",
			day_type: "None",
			start_date: "2026-10-05",
			end_date: "2026-10-11",
			...shift,
		},
	],
})
function daySheet(shift) {
	const made = sheet()
	made.vm.openDay(dayOf(shift), DAY)
	return made
}

test("the Day sheet has a Location field on the Shift Location picker, with the eyebrow label", () => {
	const day = view.slice(
		view.indexOf("<!-- Day sheet"),
		view.indexOf("</GModal>", view.indexOf("<!-- Day sheet"))
	)
	const field = day.slice(
		day.lastIndexOf("<label", day.indexOf('doctype="Shift Location"')),
		day.indexOf("</label>", day.indexOf('doctype="Shift Location"'))
	)
	assert.match(field, /<span class="g-eyebrow">\{\{ __\("Location"\) \}\}<\/span>/)
	assert.match(field, /v-model="dayForm\.shift_location"/)
})

test("the Day sheet opens with the day's location", () => {
	const { vm } = daySheet()
	assert.equal(vm.dayForm.shift_location, "Lot 5")
	const none = daySheet({ shift_location: null })
	assert.equal(none.vm.dayForm.shift_location, "")
})

test("a freshly opened Day sheet has nothing to change", () => {
	assert.equal(daySheet().vm.dayChanged.value, false)
	assert.equal(daySheet({ shift_location: null }).vm.dayChanged.value, false)
})

test("a location change alone wakes Change shift", () => {
	const { vm } = daySheet()
	vm.dayForm.shift_location = "Lot 9"
	assert.equal(vm.dayChanged.value, true)
	vm.dayForm.shift_location = "Lot 5"
	assert.equal(vm.dayChanged.value, false, "back to the prefill is no change")
	vm.dayForm.shift_location = ""
	assert.equal(vm.dayChanged.value, true, "emptying a set location is a change")
})

test("picking a location on a day that had none wakes Change shift", () => {
	const { vm } = daySheet({ shift_location: null })
	vm.dayForm.shift_location = "Lot 9"
	assert.equal(vm.dayChanged.value, true)
})

test("a changed location is sent", () => {
	const { vm, calls } = daySheet()
	vm.dayForm.shift_location = "Lot 9"
	vm.submitChange()
	assert.equal(calls.change.length, 1)
	assert.deepEqual(calls.change[0].params, {
		assignment: "HR-SHA-0001",
		date: "2026-10-08",
		shift_type: "Morning",
		shift_location: "Lot 9",
		day_type: "None",
	})
})

test("shift_location is NOT sent when only the day type or the shift changed", () => {
	const { vm, calls } = daySheet()
	vm.dayForm.day_type = "Rest Day"
	vm.dayForm.shift_type = "Night"
	vm.submitChange()
	assert.equal("shift_location" in calls.change[0].params, false, "the server keeps the location")
	assert.equal(calls.change[0].params.day_type, "Rest Day")
	assert.equal(calls.change[0].params.shift_type, "Night")
})

test("an emptied location sends an empty string, which clears it", () => {
	const { vm, calls } = daySheet()
	vm.dayForm.shift_location = ""
	vm.submitChange()
	assert.equal(calls.change[0].params.shift_location, "")
})

test("a day with no location, left empty, sends no location", () => {
	const { vm, calls } = daySheet({ shift_location: null })
	vm.dayForm.day_type = "Off Day"
	vm.submitChange()
	assert.equal("shift_location" in calls.change[0].params, false)
})
