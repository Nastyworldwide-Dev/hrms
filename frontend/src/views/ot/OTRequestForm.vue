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
					<!-- What this claims, shown UP FRONT (from HR-set eligibility) so the form is
			     never a blank mystery: the employee sees "Overtime Pay" or "Replacement
			     Leave" and what it means before touching anything. Once a day is picked it
			     also shows that day's punch-verified hours. -->
					<div
						v-if="compensation && !props.id"
						class="mx-4 mt-4 border border-divider rounded-panel p-4 flex flex-col gap-2"
					>
						<span class="g-eyebrow text-accent-ink">{{ __("You claim") }}</span>
						<span class="text-lg font-extrabold text-inkbase">
							{{ __(compensation) }}
						</span>
						<span class="text-sm text-ink-600">{{ claimTypeHint }}</span>
						<template v-if="otSummary.data">
							<!-- Overtime Pay claims HOURS, so it shows hours. Replacement Leave earns
					     whole-day blocks — showing raw hours there just confuses, so the day
					     result (from `expectation`) speaks for it. -->
							<span v-if="!isRL" class="text-sm text-ink-600">
								{{
									__("Available to claim: {0} h", [formatHoursCap(otSummary.data.punch_ot_hours)])
								}}
							</span>
							<span v-if="isRL" class="text-sm text-ink-600">{{ expectation }}</span>
						</template>
					</div>
					<!-- The dates the employee actually has unclaimed OT on — tap instead of
			     guessing a date in the picker. Days that already have a request stay in
			     the list, greyed and not selectable, so they never look like lost overtime.
			     Days worked but unclaimable (a lone check-in, a tap on no shift, a punch
			     waiting for approval…) stay too, greyed, with the reason under the date
			     and an "HR can see this" tag — the day is not hidden and nobody is asked
			     to fix a record. Only on a new request. -->
					<div v-if="displayDays.length && !props.id" class="mx-4 mt-4 flex flex-col gap-2">
						<span class="g-eyebrow">{{ __("Days you can claim") }}</span>
						<button
							v-for="d in displayDays"
							:key="d.date"
							class="w-full text-left rounded-panel border px-4 py-3 flex items-center justify-between gap-3"
							:class="
								d.disabled
									? 'border-divider bg-icon-bg cursor-not-allowed'
									: otRequest.ot_date === d.date
									? 'border-accent-ink cursor-pointer'
									: 'border-divider hover:bg-icon-bg cursor-pointer'
							"
							:disabled="d.disabled"
							:aria-disabled="d.disabled ? 'true' : undefined"
							:aria-pressed="d.disabled ? undefined : String(otRequest.ot_date === d.date)"
							@click="pickDay(d)"
						>
							<span class="flex flex-col gap-0.5 min-w-0">
								<span
									class="font-semibold"
									:class="d.disabled ? 'text-ink-700' : 'text-inkbase'"
									>{{ formatDay(d.date) }}</span
								>
								<span v-if="d.incomplete" class="text-xs text-ink-600">{{ d.reason }}</span>
							</span>
							<span
								v-if="d.incomplete"
								class="shrink-0 text-xs text-ink-700 border border-divider rounded-full px-2 py-0.5"
								>{{ d.label }}</span
							>
							<span v-else class="text-sm" :class="d.disabled ? 'text-ink-700' : 'text-ink-600'">{{
								d.label
							}}</span>
						</button>
					</div>

					<!-- An empty list used to leave a blank date picker and no answer.
			     Say which of the four situations this is. -->
					<p v-if="emptyReason && !props.id" class="mx-4 mt-4 text-sm text-ink-600" role="status">
						{{ emptyReason }}
					</p>

					<p v-if="saveError" class="mx-4 mt-3 text-sm text-ink-600" role="status">
						{{ saveError }}
					</p>
					<button
						v-if="otSummary.error"
						type="button"
						class="mx-4 mt-2 text-accent-ink"
						@click="loadSummary"
					>
						{{ __("Try again") }}
					</button>
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
import { requestStatusChip } from "@/utils/requestStatus"
import { claimDayRows, emptyClaimReason, inlineClaimError } from "./claimEmptyReason.js"

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
const claimTypeHint = computed(() => {
	const c = compensation.value
	if (c === "Overtime Pay") return __("You’ll be paid for approved overtime hours.")
	if (c === "Replacement Leave")
		return __("Your overtime becomes time off — {0} hours earns half a day.", [
			(rlHoursPerDay.value || 8) / 2,
		])
	return ""
})

// The claimable days, shaped for display (claimDayRows): Overtime Pay shows hours;
// Replacement Leave shows the whole-day blocks and DROPS days under 4h (they earn
// nothing, per HR — showing "0 days" would only confuse). Days that already have a
// request are merged in, greyed, labelled by their decision (Approved is final —
// payroll is external, so there is no "paid"). Days worked but unclaimable are
// merged in greyed with their reason, so a broken day never looks like lost overtime.
const displayDays = computed(() =>
	claimDayRows(claimableDays.value.data, {
		isRL: isRL.value,
		rlHoursPerDay: rlHoursPerDay.value,
		translate: __,
		statusLabel: requestStatusChip,
		formatHours: formatHoursCap,
	})
)

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
	return __("This gives you {0} day(s) off.", [leaveDays])
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
		.catch(() => console.warn("[OTRequestForm] selected day capacity unavailable"))
}
watch([summaryKey, () => otRequest.value.modified], loadSummary, {
	immediate: true,
	flush: "sync",
})

const saveError = computed(() => {
	if (!canEditClaim.value) return ""
	if (!summaryKey.value) return __("Choose a work date to check available overtime.")
	if (otSummary.value.error) return __("Could not check overtime. Try again before saving.")
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
