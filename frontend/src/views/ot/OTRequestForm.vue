<template>
	<GPage>
		<ion-content :fullscreen="true">
			<FormView
				v-if="formFields.data"
				doctype="OT Request"
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
								{{ __("Available to claim: {0} h", [otSummary.data.punch_ot_hours || 0]) }}
							</span>
							<span v-if="isRL" class="text-sm text-ink-600">{{ expectation }}</span>
						</template>
					</div>
					<!-- The dates the employee actually has unclaimed OT on — tap instead of
			     guessing a date in the picker. Only on a new request with something to claim. -->
					<div v-if="displayDays.length && !props.id" class="mx-4 mt-4 flex flex-col gap-2">
						<span class="g-eyebrow">{{ __("Days you can claim") }}</span>
						<button
							v-for="d in displayDays"
							:key="d.date"
							class="w-full text-left rounded-panel border px-4 py-3 flex items-center justify-between cursor-pointer"
							:class="
								otRequest.ot_date === d.date
									? 'border-accent-ink'
									: 'border-divider hover:bg-icon-bg'
							"
							@click="otRequest.ot_date = d.date"
						>
							<span class="text-inkbase font-semibold">{{ formatDay(d.date) }}</span>
							<span class="text-sm text-ink-600">{{ d.label }}</span>
						</button>
					</div>

					<!-- An empty list used to leave a blank date picker and no answer.
			     Say which of the four situations this is. -->
					<p
						v-else-if="emptyReason && !props.id"
						class="mx-4 mt-4 text-sm text-ink-600"
						role="status"
					>
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
import { IonContent } from "@ionic/vue"
import { createResource } from "frappe-ui"
import { computed, inject, ref, shallowRef, watch } from "vue"
import FormView from "@/components/FormView.vue"
import GPage from "@/components/glass/GPage.vue"
import { settings } from "@/data/settings"
import { emptyClaimReason } from "./claimEmptyReason.js"

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
		resource.fetch().catch(() => console.warn("[OTRequestForm] available dates unavailable"))
	},
	{ immediate: true, flush: "sync" }
)

const formatDay = (date) => dayjs(date).format("ddd, D MMM")

// HR's full-day ratio: overtime hours that make ONE day of replacement leave.
const rlHoursPerDay = computed(() => settings.data?.replacement_leave_hours_per_day ?? 8)

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

// The claimable days, shaped for display: Overtime Pay shows hours; Replacement
// Leave shows the whole-day blocks and DROPS days under 4h (they earn nothing, per
// HR — showing "0 days" would only confuse).
const displayDays = computed(() => {
	const days = claimableDays.value.data?.days || []
	if (!isRL.value) {
		return days.map((d) => ({ ...d, label: __("{0} h", [d.hours]) }))
	}
	return days
		.map((d) => ({ ...d, leaveDays: rlDays(d.hours) }))
		.filter((d) => d.leaveDays > 0)
		.map((d) => ({ ...d, label: __("{0} day(s) off", [d.leaveDays]) }))
})

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

const otRequest = ref({})

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
const summaryRequest = shallowRef(null)
const otSummary = computed(
	() => summaryRequest.value?.resource || { data: null, loading: false, error: null }
)
const compensation = computed(
	() => otSummary.value.data?.compensation || claimableDays.value.data?.compensation
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
	if (cap <= 0) return __("No punch-verified overtime for this date — nothing to claim")
	const claimed = Number(otRequest.value.claimed_hours)
	if (!Number.isFinite(claimed) || claimed <= 0) return __("Enter the hours to claim.")
	return claimed > cap ? __("Cannot claim more than the punch-verified {0} h", [cap]) : ""
})
watch(
	[saveError, () => formFields.data],
	() => {
		const field = formFields.data?.find((f) => f.fieldname === "claimed_hours")
		if (field) field.error_message = saveError.value
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
	if (!props.id) otRequest.value.employee = employee.data?.name
}
</script>
