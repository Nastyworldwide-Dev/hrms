<template>
	<GPage>
		<ion-content :fullscreen="true">
			<FormView
				v-if="formFields.data"
				doctype="OT Request"
				:noun="__('overtime request')"
				v-model="otRequest"
				:isSubmittable="true"
				:fields="formFields.data"
				:id="props.id"
				:showAttachmentView="false"
				:saveError="saveError"
				@validateForm="validateForm"
			>
				<template #beforeFields>
					<!-- alpha.6 C3 (owner screenshots, 24 Sep): the page was a card saying
					     "You claim · Overtime Pay", then EVERY past day as a big card —
					     claimed and unclaimable included — scrolling past the form. Now:
					     how it is paid as one line, then the open days as one grouped list
					     (at most 5, "Show more"), the rest folded into two counted rows
					     (NN/g: the few that matter, the rest on request). -->
					<div v-if="!props.id" class="g-form-body g-ot-days">
						<section v-if="dayGroups.open.length" class="g-form-section">
							<h2 class="g-form-section__title">{{ __("Pick a day") }}</h2>
							<div class="g-form-group" role="radiogroup" :aria-label="__('Pick a day')">
								<button
									v-for="d in dayGroups.open"
									:key="d.date"
									type="button"
									role="radio"
									class="g-form-row g-form-row--action g-ot-day"
									:aria-checked="String(otRequest.ot_date === d.date)"
									@click="pickDay(d)"
								>
									<span class="g-form-row__label">{{ formatDay(d.date) }}</span>
									<span class="g-ot-day__value">{{ d.label }}</span>
									<Check
										v-if="otRequest.ot_date === d.date"
										class="g-ot-day__check"
										aria-hidden="true"
									/>
								</button>
								<!-- The check failed: retry is a row in the group (alpha.7 0.5),
								     not a floating lime link. -->
								<button
									v-if="otSummary.error"
									type="button"
									class="g-form-row g-form-row--action g-ot-more"
									@click="loadSummary"
								>
									{{ __("Try again") }}
								</button>
								<button
									v-if="dayGroups.moreOpen"
									type="button"
									class="g-form-row g-form-row--action g-ot-more"
									@click="showAllDays = true"
								>
									{{ __("Show {0} more", [dayGroups.moreOpen]) }}
								</button>
							</div>
							<!-- One footer says what the picked day is worth and how it is
							     paid, or what went wrong (alpha.7 0.5; HIG: guidance is the
							     group footer, never a line floating between groups). -->
							<p class="g-form-footer" role="status">{{ dayFooter }}</p>
						</section>

						<section
							v-if="dayGroups.claimed.length || dayGroups.cannot.length"
							class="g-form-section"
						>
							<div class="g-form-group">
								<button
									v-if="dayGroups.claimed.length"
									type="button"
									class="g-form-row g-form-row--action g-ot-fold"
									:aria-expanded="String(openFold === 'claimed')"
									@click="openFold = openFold === 'claimed' ? '' : 'claimed'"
								>
									<span class="g-form-row__label">{{ __("Already claimed") }}</span>
									<span class="g-ot-day__value">{{ dayGroups.claimed.length }}</span>
								</button>
								<div
									v-for="d in openFold === 'claimed' ? dayGroups.claimed : []"
									:key="`c${d.date}`"
									class="g-form-row g-ot-sub"
								>
									<span class="g-form-row__label">{{ formatDay(d.date) }}</span>
									<span class="g-ot-day__value">{{ d.label.replace(/^Claimed · /, "") }}</span>
								</div>
								<button
									v-if="dayGroups.cannot.length"
									type="button"
									class="g-form-row g-form-row--action g-ot-fold"
									:aria-expanded="String(openFold === 'cannot')"
									@click="openFold = openFold === 'cannot' ? '' : 'cannot'"
								>
									<span class="g-form-row__label">{{ __("Can't claim yet") }}</span>
									<span class="g-ot-day__value">{{ dayGroups.cannot.length }}</span>
								</button>
								<div
									v-for="d in openFold === 'cannot' ? dayGroups.cannot : []"
									:key="`x${d.date}`"
									class="g-form-row g-form-row--stacked g-ot-sub"
								>
									<span class="g-form-row__label">{{ formatDay(d.date) }}</span>
									<span class="g-ot-reason">{{ d.reason }}</span>
								</div>
							</div>
							<p v-if="dayGroups.cannot.length" class="g-form-footer">
								{{ __("HR will sort these out. You don't need to do anything.") }}
							</p>
						</section>
					</div>

					<!-- An empty list used to leave a blank date picker and no answer.
			     Say which of the four situations this is. -->
					<p
						v-if="emptyReason && !props.id"
						class="g-empty-line mx-4 mt-4 text-sm text-ink-600"
						role="status"
					>
						{{ emptyReason }}
					</p>
				</template>
			</FormView>
			<ResourceError :resource="formFields" back what="the overtime request form" />
		</ion-content>
	</GPage>
</template>

<script setup>
import { useRoute } from "vue-router"
import { dateFromRoute } from "@/utils/dateFromRoute"
import { IonContent } from "@ionic/vue"
import { createResource } from "frappe-ui"
import { computed, inject, ref, shallowRef, watch } from "vue"
import FormView from "@/components/FormView.vue"
import GPage from "@/components/glass/GPage.vue"
import { settings } from "@/data/settings"
import { formatHoursCap } from "@/utils/formatters"
import { hoursAsTime } from "@/utils/daySheet"
import { countOf } from "@/utils/countWords"
import { requestStatusChip } from "@/utils/requestStatus"
import {
	claimDayGroups,
	claimDayRows,
	emptyClaimReason,
	inlineClaimError,
	summaryFailure,
} from "./claimEmptyReason.js"
import { Check } from "lucide-vue-next"

const employee = inject("$employee")
const __ = inject("$translate")
const dayjs = inject("$dayjs")

// The dates the employee has unclaimed OT on — offered as quick-picks so they tap
// a day instead of guessing one in the picker (the card only gave them a total).
const claimableRequest = shallowRef(null)
const claimableDays = computed(() => claimableRequest.value || {})
watch(
	() => employee.data?.name,
	(employeeId) => {
		claimableRequest.value = null
		if (!employeeId) return
		console.debug("[OTRequestForm] loading available dates")
		const resource = createResource({
			url: "hrms.api.get_claimable_ot_summary",
			params: { employee: employeeId },
		})
		claimableRequest.value = resource
		resource.fetch()?.catch?.(() => console.warn("[OTRequestForm] available dates unavailable"))
	},
	{ immediate: true, flush: "sync" }
)

const formatDay = (date) => dayjs(date).format("ddd, D MMM")

// HR's full-day ratio: overtime hours that make ONE day of replacement leave.
const rlHoursPerDay = computed(() => settings.data?.replacement_leave_hours_per_day ?? 8)

// Each employee/date owns a summary resource (loadSummary below swaps it);
// declared ahead of every computed that reads it so setup never touches a
// binding still in its temporal dead zone (the 14 Sep KPI/OT crash class).
const summaryRequest = shallowRef(null)
const otSummary = computed(
	() => summaryRequest.value?.resource || { data: null, loading: false, error: null }
)
const compensation = computed(
	() => otSummary.value.data?.compensation || claimableDays.value.data?.compensation
)

const isRL = computed(() => compensation.value === "Replacement Leave")

// Replacement leave earned by ONE day's OT, in whole 4-hour blocks — mirrors the
// backend replacement_leave_days: floor(hours / (ratio/2)) * 0.5. Under 4h = 0.
// Per day, never accumulated: a short day earns nothing.
const rlDays = (hours) => {
	const half = (rlHoursPerDay.value || 8) / 2
	if (!hours || half <= 0) return 0
	return Math.floor(hours / half) * 0.5
}

// One plain line telling the employee what their claim type means.

// The claimable days, shaped for display (claimDayRows): Overtime Pay shows hours;
// Replacement Leave shows the whole-day blocks and DROPS days under 4h (they earn
// nothing, per HR — showing "0 days" would only confuse). Days that already have a
// request are merged in, greyed, labelled by their decision (Approved is final —
// payroll is external, so there is no "paid"). Days worked but unclaimable are
// merged in greyed with their reason, so a broken day never looks like lost overtime.
//: Hours as time ("5h 40m", ruling C8), rounded DOWN to the minute: these are
//: caps, and a rounded-up figure offers time the cap check refuses.
const capAsTime = (h) => hoursAsTime(Math.floor((Number(h) || 0) * 60 + 1e-9) / 60)

const displayDays = computed(() =>
	claimDayRows(claimableDays.value.data, {
		isRL: isRL.value,
		rlHoursPerDay: rlHoursPerDay.value,
		translate: __,
		statusLabel: requestStatusChip,
		formatHours: capAsTime,
	})
)

//: Folded groups and "Show more" (alpha.6 C3).
const showAllDays = ref(false)
const openFold = ref("")
const dayGroups = computed(() => claimDayGroups(displayDays.value, { showAll: showAllDays.value }))

function pickDay(d) {
	if (d.disabled) return
	otRequest.value.ot_date = d.date
}

// E9-UX: the red "Choose a work date…" under Claimed hours showed the moment the
// form opened, before the employee had done anything. It waits until they touch
// the date or try to save; the grey hint under the panel still shows from the start.
const dateTouched = ref(false)
const saveAttempted = ref(false)

// Why the list above is empty, when it is. "Already claimed", "no overtime" and
// "every day is under the replacement-leave threshold" are very different
// answers that all rendered as an empty screen and a date picker.
const emptyReason = computed(() =>
	emptyClaimReason(claimableDays.value.data, {
		isRL: isRL.value,
		rlHoursPerDay: rlHoursPerDay.value,
		translate: __,
	})
)

// What to expect from this claim — pay for hours, or the whole-day blocks of leave.
const expectation = computed(() => {
	const d = otSummary.value.data
	if (!d) return ""
	if (d.compensation === "Overtime Pay") return ""
	const leaveDays = rlDays(d.punch_ot_hours || 0)
	const half = (rlHoursPerDay.value || 8) / 2
	if (leaveDays <= 0) {
		return __("Under {0}h in a day earns no replacement leave ({0}h = ½ day).", [half])
	}
	return __("This gives you {0} off.", [countOf(leaveDays, __("day"))])
})

const props = defineProps({
	id: {
		type: String,
		required: false,
	},
})

//: A Calendar day's "Claim" opens with that day chosen (?date=, approved
//: Calendar plan D2).
const route = useRoute()
const startDay = props.id ? null : dateFromRoute(route.query)
const otRequest = ref(startDay ? { ot_date: startDay } : {})

// Declared after otRequest on purpose: watch() reads its source at creation, and a
// ref declared below it crashes setup (the KPI page did exactly this, d8c5f58b4).
watch(
	() => otRequest.value.ot_date,
	(date) => {
		if (date) dateTouched.value = true
	}
)

const formFields = createResource({
	url: "hrms.api.get_doctype_fields",
	params: { doctype: "OT Request" },
	auto: true,
	transform(data) {
		if (props.id) return data
		return data
			.filter(
				// status: the decision is displayed on detail, never offered on create —
				// the requester is not the person who decides (leave/Form.vue convention)
				// compensation/punch_ot_hours/shift move into the claim summary panel below
				// so the employee sees WHAT they are claiming, not bare read-only rows.
				(field) =>
					![
						"employee",
						"employee_name",
						"department",
						"company",
						"status",
						"compensation",
						"punch_ot_hours",
						"shift",
					].includes(field.fieldname)
			)
			.map((field) => {
				// reason is back and MANDATORY — the approver needs the why, and HR asked
				// for it after it was briefly removed.
				if (field.fieldname === "explanation") field.reqd = 1
				return field
			})
	},
})

// Each employee/date owns a resource; stale responses cannot change the form.
const canEditClaim = computed(
	() =>
		!props.id ||
		(otRequest.value.name === props.id &&
			otRequest.value.docstatus === 0 &&
			otRequest.value.employee === employee.data?.name)
)
const summaryKey = computed(() => {
	if (!canEditClaim.value) return ""
	const employeeId = props.id ? otRequest.value.employee : employee.data?.name
	return employeeId && otRequest.value.ot_date
		? JSON.stringify([employeeId, otRequest.value.ot_date, props.id || ""])
		: ""
})

//: The day was chosen from "Pick a day": asking for the date again below would
//: show one fact twice (alpha.7 0.4). The field stays for a day not in the list.
const pickedFromList = computed(
	() =>
		!props.id && displayDays.value.some((d) => !d.disabled && d.date === otRequest.value.ot_date)
)
watch(
	[pickedFromList, () => formFields.data],
	() => {
		const field = formFields.data?.find((f) => f.fieldname === "ot_date")
		if (field) field.hidden = pickedFromList.value ? 1 : 0
	},
	{ immediate: true }
)

//: The Pick-a-day footer: how it is paid and what the day is worth, or the
//: state of the check. Never red: an error for the hours goes under the row.
const dayFooter = computed(() => {
	const paid = isRL.value ? __("Paid as time off") : __("Paid as overtime")
	if (!summaryKey.value) return paid
	if (otSummary.value.error) return summaryFailure(otSummary.value.error, __)
	if (otSummary.value.loading || !otSummary.value.data) return __("Checking this day…")
	if (isRL.value) return expectation.value ? `${paid} · ${expectation.value}` : paid
	return __("{0} · {1} to claim", [paid, capAsTime(otSummary.value.data.punch_ot_hours)])
})

let previousKey = ""
let retainedClaim = null
function loadSummary() {
	const key = summaryKey.value
	const preserve = key && (key === previousKey || (!previousKey && props.id))
	retainedClaim = preserve ? otRequest.value.claimed_hours ?? retainedClaim : null
	previousKey = key || previousKey
	summaryRequest.value = null
	if (!canEditClaim.value) return
	// Reloading the same saved day is a check, not an edit. Only a changed
	// selection clears model values; saveError still blocks unsettled saves.
	if (!preserve) {
		Object.assign(otRequest.value, {
			claimed_hours: null,
			punch_ot_hours: null,
			shift: null,
			compensation: null,
		})
	}
	if (!key) return
	console.debug("[OTRequestForm] checking selected day capacity")
	const [employeeId, date] = JSON.parse(key)
	const entry = {
		key,
		resource: createResource({
			url: "hrms.api.get_ot_claim_summary",
			params: { employee: employeeId, date },
			transform(data) {
				if (
					typeof data?.punch_ot_hours !== "number" ||
					!Number.isFinite(data.punch_ot_hours) ||
					data.punch_ot_hours < 0 ||
					!["Overtime Pay", "Replacement Leave"].includes(data.compensation)
				)
					throw new Error("Invalid overtime summary")
				return data
			},
			onError(error) {
				// The reason the live check failed (24 Sep) was never recorded.
				console.error("[OTRequestForm] overtime check failed", {
					exc_type: error?.exc_type,
					message: (error?.messages || [])[0] || error?.message,
				})
			},
			onSuccess(data) {
				if (summaryRequest.value !== entry || summaryKey.value !== key) return
				const cap = data.punch_ot_hours
				Object.assign(otRequest.value, {
					shift: data.shift,
					compensation: data.compensation,
					punch_ot_hours: cap,
					claimed_hours: otRequest.value.claimed_hours ?? retainedClaim ?? cap,
				})
			},
		}),
	}
	summaryRequest.value = entry
	entry.resource
		.fetch()
		?.catch?.(() => console.warn("[OTRequestForm] selected day capacity unavailable"))
}
watch([summaryKey, () => otRequest.value.modified], loadSummary, {
	immediate: true,
	flush: "sync",
})

const saveError = computed(() => {
	if (!canEditClaim.value) return ""
	if (!summaryKey.value) return __("Choose a work date to check available overtime.")
	if (otSummary.value.error) return summaryFailure(otSummary.value.error, __)
	if (otSummary.value.loading || !otSummary.value.data)
		return __("Checking overtime for this date…")
	const cap = otRequest.value.punch_ot_hours
	if (typeof cap !== "number" || !Number.isFinite(cap))
		return __("Could not check overtime. Try again before saving.")
	// A zero is an answer, not an explanation. Fifteen different situations end
	// here and they all used to read the same, so somebody told they had no
	// overtime could not tell whether they genuinely worked none, whether their
	// punches never attached to a shift, whether overtime is switched off on
	// that shift, or whether a check-out is simply missing. Only the first of
	// those is theirs to answer; the rest need HR, and nothing said so.
	if (cap <= 0)
		return (
			otSummary.value.data?.no_overtime_reason ||
			__("No punch-verified overtime for this date — nothing to claim")
		)
	const claimed = Number(otRequest.value.claimed_hours)
	if (!Number.isFinite(claimed) || claimed <= 0) return __("Enter the hours to claim.")
	return claimed > cap
		? __("Cannot claim more than the punch-verified {0} h", [formatHoursCap(cap)])
		: ""
})
// What the Claimed hours field shows in red: every error, except that "choose a
// date" waits for the employee to act first (see dateTouched). saveError itself
// is untouched, so the Save button stays disabled and the grey hint still shows.
const inlineError = computed(() =>
	inlineClaimError(saveError.value, {
		hasDate: Boolean(summaryKey.value),
		// A pending OR failed day check is said once, in the Pick-a-day footer
		// (dayFooter), not a second time in red under Hours (alpha.7 0.3/0.5).
		loading:
			Boolean(summaryKey.value) &&
			(Boolean(otSummary.value.error) ||
				otSummary.value.loading ||
				!otSummary.value.data),
		touched: dateTouched.value,
		saveAttempted: saveAttempted.value,
	})
)
watch(
	[inlineError, () => formFields.data],
	() => {
		const field = formFields.data?.find((f) => f.fieldname === "claimed_hours")
		if (field) field.error_message = inlineError.value
	},
	{ immediate: true, flush: "sync" }
)

watch(
	() => otRequest.value.employee,
	(employee_id) => {
		if (props.id && employee_id && employee_id !== employee.data?.name) {
			formFields.data?.map((field) => (field.read_only = true))
		}
	}
)

function validateForm() {
	saveAttempted.value = true
	if (!props.id) otRequest.value.employee = employee.data?.name
}
</script>
