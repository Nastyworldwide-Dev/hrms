<template>
	<BaseLayout :pageTitle="__('Team roster')">
		<template #body>
			<GPullRefresh @refresh="refresh" />
			<div
				class="flex flex-col gap-5 w-full max-w-content-column-lg mx-auto px-4 pt-4 pb-4 lg:py-7"
			>
				<!-- HR-only team selector: HR has no direct reports, so without this
				     the roster is empty. Same pattern as TeamDashboard. -->
				<div v-if="teamManagers.data?.length" class="flex flex-row items-center gap-2">
					<span class="g-eyebrow flex-none">{{ __("Team of") }}</span>
					<GSelect
						class="flex-1 min-w-0"
						:aria-label="__('Team of')"
						:options="managerOptions"
						:model-value="selectedManager"
						:placeholder="__('Select a team')"
						@update:model-value="onManagerPicked"
					/>
				</div>

				<!-- week navigation -->
				<div class="flex flex-row items-center justify-between">
					<GIconButton :label="__('Previous week')" @click="changeWeek(-1)">
						<ChevronLeft class="h-4 w-4" />
					</GIconButton>
					<span class="g-datenav__label" data-visual-mask>{{ weekLabel }}</span>
					<GIconButton :label="__('Next week')" @click="changeWeek(1)">
						<ChevronRight class="h-4 w-4" />
					</GIconButton>
				</div>

				<ResourceError :resource="teamRoster" what="your team's roster" />

				<!-- one section per member: identity + a 7-day shift strip -->
				<template v-if="teamRoster.data?.members?.length">
					<div
						v-for="member in teamRoster.data.members"
						:key="member.name"
						class="flex flex-col gap-2.5"
					>
						<div class="flex items-start justify-between gap-2">
							<div class="flex flex-col min-w-0">
								<span class="text-panel-title text-inkbase truncate">{{
									member.is_self ? __("You") : member.employee_name
								}}</span>
								<span
									v-if="member.branch || member.department"
									class="text-kra-label text-ink-600 truncate"
								>
									{{ member.branch || departmentLabel(member.department) }}
								</span>
							</div>
							<button
								class="g-seclink g-focusable text-kra-label text-accent-ink flex-none"
								@click="openAssign(member)"
							>
								{{ __("Assign") }}
							</button>
						</div>
						<!-- day strip; scrolls horizontally on a narrow phone -->
						<div class="flex gap-1.5 overflow-x-auto pb-1">
							<button
								v-for="day in weekDays"
								:key="day.iso"
								type="button"
								class="g-focusable flex flex-col items-center justify-center flex-none w-11 py-1.5 rounded-well border border-divider"
								:class="shiftOn(member, day) ? 'bg-surface' : ''"
								:aria-label="dayLabel(member, day)"
								@click="openDay(member, day)"
							>
								<span class="text-caption text-ink-600">{{ day.dow }}</span>
								<span
									class="text-button-label font-semibold"
									:class="shiftOn(member, day) ? 'text-inkbase' : 'text-ink-500'"
								>
									{{ shiftCode(member, day) }}
								</span>
								<span
									v-if="dayTypeMark(member, day)"
									aria-hidden="true"
									class="text-caption font-semibold text-accent-ink"
								>
									{{ dayTypeMark(member, day) }}
								</span>
							</button>
						</div>
					</div>
				</template>

				<div v-else-if="!teamRoster.loading" class="text-caption text-ink-600 text-center py-8">
					{{ __("No team members to roster. You only see people who report to you.") }}
				</div>
				<div v-if="teamRoster.loading" class="flex flex-col gap-2 mt-2" aria-hidden="true">
					<GSkeleton v-for="n in 3" :key="n" height="44px" radius="var(--g-radius-panel)" />
				</div>
			</div>

			<!-- Assign sheet: the fence lives on the server; this only collects input -->
			<GModal :isOpen="assignOpen" :title="__('Assign shift')" @did-dismiss="assignOpen = false">
				<template #actionSheet>
					<div class="flex flex-col gap-4 pt-1">
						<div class="text-kra-label text-ink-600">{{ assignTarget?.employee_name }}</div>
						<div class="flex flex-col gap-1.5">
							<label class="flex flex-col gap-1.5">
								<span class="g-eyebrow">{{ __("Shift type") }}</span>
								<Link
									doctype="Shift Type"
									v-model="form.shift_type"
									:describedby="form.shift_type && canSubmit ? '' : 'assign-shift-hint'"
								/>
							</label>
							<span
								v-if="!form.shift_type || !canSubmit"
								id="assign-shift-hint"
								class="text-caption text-ink-600"
							>
								{{ shiftHint }}
							</span>
						</div>
						<label v-if="form.shift_type" class="flex flex-col gap-1.5">
							<span class="g-eyebrow">{{ __("Location") }}</span>
							<Link doctype="Shift Location" v-model="form.shift_location" />
						</label>
						<GSelect :label="__('Day type')" :options="dayTypeOptions" v-model="form.day_type" />
						<div class="flex gap-3">
							<label class="flex flex-col gap-1.5 flex-1">
								<span class="g-eyebrow">{{ __("From") }}</span>
								<input
									type="date"
									v-model="form.start_date"
									class="g-touch bg-surface border border-divider rounded-input p-2.5 text-inkbase"
								/>
							</label>
							<label class="flex flex-col gap-1.5 flex-1">
								<span class="g-eyebrow">{{ __("To") }}</span>
								<input
									type="date"
									v-model="form.end_date"
									class="g-touch bg-surface border border-divider rounded-input p-2.5 text-inkbase"
								/>
							</label>
						</div>
						<GButton
							:label="__('Assign shift')"
							:pending-label="__('Assigning…')"
							:disabled="!canSubmit"
							:aria-describedby="canSubmit ? undefined : 'assign-shift-hint'"
							:pending="assignShift.loading || setDayType.loading"
							@click="submitAssign"
						/>
					</div>
				</template>
			</GModal>

			<!-- Day sheet: change or remove one day's shift. Server fences and
			     refuses a day that already has punches (owner ruling a, 2 Oct 2026). -->
			<GModal :isOpen="dayOpen" :title="dayTitle" @did-dismiss="dayOpen = false">
				<template #actionSheet>
					<div class="flex flex-col gap-4 pt-1">
						<div class="text-kra-label text-ink-600">
							{{ dayTarget?.member.employee_name }} · {{ dayTarget?.shift.shift_type }}
						</div>
						<label class="flex flex-col gap-1.5">
							<span class="g-eyebrow">{{ __("Change to") }}</span>
							<Link doctype="Shift Type" v-model="dayForm.shift_type" />
						</label>
						<label class="flex flex-col gap-1.5">
							<span class="g-eyebrow">{{ __("Location") }}</span>
							<Link doctype="Shift Location" v-model="dayForm.shift_location" />
						</label>
						<GSelect
							:label="__('Day type')"
							:options="dayTypeOptions"
							v-model="dayForm.day_type"
						/>
						<GButton
							:label="__('Change shift')"
							:pending-label="__('Changing…')"
							:disabled="!dayChanged"
							:pending="changeShiftDay.loading"
							@click="submitChange"
						/>
						<GButton
							danger
							:label="__('Remove this day')"
							:pending-label="__('Removing…')"
							:pending="removeShiftDay.loading"
							@click="submitRemove"
						/>
					</div>
				</template>
			</GModal>
		</template>
	</BaseLayout>
</template>

<script setup>
import { departmentLabel } from "@/utils/departmentLabel"
import { ChevronLeft, ChevronRight } from "lucide-vue-next"
import { computed, defineAsyncComponent, inject, reactive, ref, onMounted } from "vue"
import { gToast } from "@/components/glass/toast"
import GSelect from "@/components/glass/GSelect.vue"
import GSkeleton from "@/components/glass/GSkeleton.vue"

import BaseLayout from "@/components/BaseLayout.vue"
import GIconButton from "@/components/glass/GIconButton.vue"
import GModal from "@/components/glass/GModal.vue"
import GButton from "@/components/glass/GButton.vue"
import Link from "@/components/Link.vue"
import ResourceError from "@/components/ResourceError.vue"
import {
	teamRoster,
	assignShift,
	setDayType,
	teamManagers,
	changeShiftDay,
	removeShiftDay,
} from "@/data/team"
import { buildManagerOptions } from "@/utils/team"

const __ = inject("$translate")
const dayjs = inject("$dayjs")

// HR-only "Team of" selector — HR has no direct reports, so they must pick a
// manager to see/roster that team. Non-HR receive [] and the selector hides.
const selectedManager = ref("")
const selectedOption = ref(null)
const managerOptions = computed(() =>
	buildManagerOptions(teamManagers.data || [], __("Select a team"))
)
function onManagerPicked(value) {
	const option = value ? { value } : null
	selectedOption.value = option
	selectedManager.value = option?.value || ""
	load()
}

// Monday-anchored week the grid is showing
const weekStart = ref(dayjs().startOf("week").add(1, "day"))

const weekDays = computed(() =>
	Array.from({ length: 7 }, (_, i) => {
		const d = weekStart.value.add(i, "day")
		return { iso: d.format("YYYY-MM-DD"), dow: d.format("dd").slice(0, 2) }
	})
)
const weekLabel = computed(
	() => `${weekStart.value.format("D MMM")} – ${weekStart.value.add(6, "day").format("D MMM")}`
)

function load() {
	teamRoster.submit({
		start_date: weekStart.value.format("YYYY-MM-DD"),
		end_date: weekStart.value.add(6, "day").format("YYYY-MM-DD"),
		manager: selectedManager.value || undefined,
	})
}
//: Loaded on first use, not in the first download (alpha.13: Ionic's
//: refresher is 41 KB, and nobody pulls before the page has drawn).
const GPullRefresh = defineAsyncComponent(() => import("@/components/glass/GPullRefresh.vue"))

//: Pull to refresh reloads what the roster shows (6 Oct 2026: a pull did nothing here).
//: reload() repeats the last load, so the week and the picked team stay.
async function refresh(event) {
	console.info("[TeamRoster] pull-to-refresh")
	await Promise.allSettled([teamRoster.reload(), teamManagers.reload()])
	event.target?.complete?.()
}
function changeWeek(n) {
	weekStart.value = weekStart.value.add(n * 7, "day")
	load()
}
onMounted(load)

// a shift covers a day when start_date <= day <= end_date (open-ended = ongoing)
function shiftOn(member, day) {
	return (member.shifts || []).find(
		(s) =>
			!dayjs(day.iso).isBefore(dayjs(s.start_date)) &&
			(!s.end_date || !dayjs(day.iso).isAfter(dayjs(s.end_date)))
	)
}
function shiftCode(member, day) {
	const s = shiftOn(member, day)
	if (!s) return "—"
	// short, legible code from the shift type name (e.g. "Night" -> "N")
	return String(s.shift_type || "?")
		.replace(/[^A-Za-z0-9]/g, "")
		.slice(0, 1)
		.toUpperCase()
}

// --- change / remove one day ---
const dayOpen = ref(false)
const dayTarget = ref(null)
const dayForm = reactive({ shift_type: "", shift_location: "", day_type: "None" })

// HR, 2 Oct 2026: the roster's Day Type sets the kind of day and its OT rate.
// "None" follows the holiday calendar.
const dayTypeOptions = computed(() => [
	{ label: __("Follows the calendar"), value: "None" },
	{ label: __("Work day"), value: "Work Day" },
	{ label: __("Rest day"), value: "Rest Day" },
	{ label: __("Off day"), value: "Off Day" },
	{ label: __("Public holiday"), value: "Public Holiday" },
])
const DAY_TYPE_MARKS = { "Rest Day": "R", "Off Day": "O", "Public Holiday": "PH", "Work Day": "W" }
// a day with no shift can still carry a Roster Day marker (Off / Rest / Public holiday)
const markerOn = (member, day) => (shiftOn(member, day) ? "" : member.markers?.[day.iso] || "")
function dayTypeMark(member, day) {
	return DAY_TYPE_MARKS[shiftOn(member, day)?.day_type || markerOn(member, day)] || ""
}
// the day's location as the server holds it: empty and missing are the same
const locationChanged = () =>
	(dayForm.shift_location || "") !== (dayTarget.value?.shift?.shift_location || "")
const dayChanged = computed(() => {
	const shift = dayTarget.value?.shift
	if (!shift) return false
	const type = dayForm.shift_type || shift.shift_type
	return (
		type !== shift.shift_type ||
		dayForm.day_type !== (shift.day_type || "None") ||
		locationChanged()
	)
})
const dayTitle = computed(() =>
	dayTarget.value ? dayjs(dayTarget.value.date).format("ddd D MMM") : ""
)

function dayLabel(member, day) {
	const s = shiftOn(member, day)
	const word = s ? s.day_type : markerOn(member, day)
	const type =
		word && word !== "None" ? dayTypeOptions.value.find((o) => o.value === word)?.label : ""
	return `${member.employee_name}, ${day.iso}: ${s ? s.shift_type : __("No shift")}${
		type ? `, ${type}` : ""
	}`
}
// an empty day goes straight to Assign for that date; a rostered day opens the sheet
function openDay(member, day) {
	const shift = shiftOn(member, day)
	if (!shift) {
		openAssign(member)
		form.start_date = form.end_date = day.iso
		form.day_type = markerOn(member, day) || "None"
		return
	}
	dayTarget.value = { member, shift, date: day.iso }
	dayForm.shift_type = ""
	dayForm.shift_location = shift.shift_location || ""
	dayForm.day_type = shift.day_type || "None"
	dayOpen.value = true
}
function onDayDone(title) {
	dayOpen.value = false
	gToast({ title, variant: "success" })
	load()
}
const dayError = (fallback) => (e) =>
	gToast({ title: e?.messages?.[0] || fallback, variant: "error" })

function submitChange() {
	const t = dayTarget.value
	changeShiftDay.submit(
		{
			assignment: t.shift.name,
			date: t.date,
			shift_type: dayForm.shift_type || t.shift.shift_type,
			// only a changed location is sent: the server keeps the day's own otherwise,
			// and "" clears it (owner, R3a, 7 Oct 2026)
			...(locationChanged() ? { shift_location: dayForm.shift_location || "" } : {}),
			day_type: dayForm.day_type,
		},
		{
			onSuccess: () => onDayDone(__("Shift changed")),
			onError: dayError(__("Could not change shift")),
		}
	)
}
function submitRemove() {
	const t = dayTarget.value
	removeShiftDay.submit(
		{ assignment: t.shift.name, date: t.date },
		{
			onSuccess: () => onDayDone(__("Shift removed")),
			onError: dayError(__("Could not remove shift")),
		}
	)
}

// --- assign ---
const assignOpen = ref(false)
const assignTarget = ref(null)
const form = reactive({
	shift_type: "",
	shift_location: "",
	day_type: "None",
	start_date: "",
	end_date: "",
})

function openAssign(member) {
	assignTarget.value = member
	form.shift_type = ""
	form.shift_location = ""
	form.day_type = "None"
	form.start_date = weekStart.value.format("YYYY-MM-DD")
	form.end_date = weekStart.value.add(6, "day").format("YYYY-MM-DD")
	assignOpen.value = true
}
// Shift type is optional: with no shift, a day type alone saves a day marker
// (HR, 6 Oct 2026: an "Off day" with no shift could not be saved).
// a day with no shift is never a work day (owner, 7 Oct 2026)
const NO_SHIFT_DAY_TYPES = ["Off Day", "Rest Day", "Public Holiday"]
const hasDayType = (value) => NO_SHIFT_DAY_TYPES.includes(value)
// with no shift the hint says how to mark a day, or why Save is still grey
const shiftHint = computed(() =>
	!form.start_date
		? __("Pick a From date.")
		: hasDayType(form.day_type) || !form.day_type || form.day_type === "None"
		? __("Leave empty and pick a Day type to mark the day only (Off, Rest, Public holiday).")
		: __("Pick a shift, or choose Off day, Rest day or Public holiday.")
)
const canSubmit = computed(() =>
	Boolean(form.start_date && (form.shift_type || hasDayType(form.day_type)))
)
// "8 Oct", "8–10 Oct", "30 Sep – 2 Oct": the days a marker was saved for
function markedDays(from, to) {
	const start = dayjs(from)
	const end = to ? dayjs(to) : start
	if (!end.isAfter(start, "day")) return start.format("D MMM")
	return start.isSame(end, "month")
		? `${start.format("D")}–${end.format("D MMM")}`
		: `${start.format("D MMM")} – ${end.format("D MMM")}`
}
const assignError = (fallback) => (e) =>
	gToast({ title: e?.messages?.[0] || fallback, variant: "error" })

function submitAssign() {
	if (!canSubmit.value) return
	if (!form.shift_type) return submitDayMarker()
	assignShift.submit(
		{
			employee: assignTarget.value.name,
			company: assignTarget.value.company,
			shift_type: form.shift_type,
			start_date: form.start_date,
			end_date: form.end_date || null,
			status: "Active",
			shift_location: form.shift_location || null,
			day_type: form.day_type,
		},
		{
			onSuccess: () => {
				assignOpen.value = false
				gToast({ title: __("Shift assigned"), variant: "success" })
				load()
			},
			onError: assignError(__("Could not assign shift")),
		}
	)
}
// No shift: only the kind of day is saved. A marker has no location, so the
// Location field is ignored here.
function submitDayMarker() {
	const label = dayTypeOptions.value.find((o) => o.value === form.day_type)?.label
	const days = markedDays(form.start_date, form.end_date)
	setDayType.submit(
		{
			employee: assignTarget.value.name,
			from_date: form.start_date,
			to_date: form.end_date || null,
			day_type: form.day_type,
		},
		{
			onSuccess: () => {
				assignOpen.value = false
				gToast({ title: __("{0} saved for {1}", [label, days]), variant: "success" })
				load()
			},
			onError: assignError(__("Could not save the day type")),
		}
	)
}
</script>
