<template>
	<GPage>
		<ion-content :fullscreen="true">
			<!-- Claim summary from the engine: the employee sees their claim TYPE (pay
			     or leave, from HR-set eligibility), how many hours are claimable, and
			     what to expect — before they enter anything. Shown once a date is picked
			     on a new request. -->
			<div
				v-if="otSummary.data && !props.id"
				class="mx-4 mt-4 border border-divider rounded-panel p-4 flex flex-col gap-2"
			>
				<span class="g-eyebrow">{{ __("Your claim") }}</span>
				<span class="text-lg font-extrabold text-inkbase">
					{{ __(otSummary.data.compensation) }}
				</span>
				<span class="text-sm text-ink-600">
					{{
						__("Overtime worked: {0} h — claim up to that.", [otSummary.data.punch_ot_hours || 0])
					}}
				</span>
				<span class="text-sm text-ink-600">{{ expectation }}</span>
			</div>
			<FormView
				v-if="formFields.data"
				doctype="OT Request"
				v-model="otRequest"
				:isSubmittable="true"
				:fields="formFields.data"
				:id="props.id"
				:showAttachmentView="true"
				:requireAttachment="false"
				@validateForm="validateForm"
			/>
			<ResourceError :resource="formFields" back what="the overtime request form" />
		</ion-content>
	</GPage>
</template>

<script setup>
import GPage from "@/components/glass/GPage.vue"
import { IonContent } from "@ionic/vue"
import { createResource } from "frappe-ui"
import { ref, computed, watch, inject } from "vue"

import FormView from "@/components/FormView.vue"
import { settings } from "@/data/settings"
import { formatLeaveDays } from "@/utils/formatters"

const employee = inject("$employee")
const __ = inject("$translate")

// HR's configurable ratio: banked overtime hours per day of replacement leave.
const rlHoursPerDay = computed(() => settings.data?.replacement_leave_hours_per_day ?? 8)

// What the employee should expect from this claim — told plainly, from the engine,
// so they know before they submit whether it pays out or becomes leave, and roughly
// how much. The approver still decides yes/no; this only sets the expectation.
const expectation = computed(() => {
	const d = otSummary.data
	if (!d) return ""
	if (d.compensation === "Overtime Pay") {
		return __("This pays out as overtime — you'll be paid for the hours you claim.")
	}
	const days = rlHoursPerDay.value ? (d.punch_ot_hours || 0) / rlHoursPerDay.value : 0
	return __("This banks as replacement leave — up to {0} h ≈ {1} day(s) off.", [
		d.punch_ot_hours || 0,
		formatLeaveDays(days),
	])
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
		return data.filter(
			// status: the decision is displayed on detail, never offered on create —
			// the requester is not the person who decides (leave/Form.vue convention)
			// compensation/punch_ot_hours/shift move into the claim summary panel below
			// so the employee sees WHAT they are claiming, not bare read-only rows;
			// explanation is removed outright (the approver decides, a reason adds nothing).
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
					"explanation",
				].includes(field.fieldname)
		)
	},
})

// live punch-verified summary for the picked day
const otSummary = createResource({
	url: "hrms.api.get_ot_claim_summary",
	onSuccess(data) {
		otRequest.value.shift = data.shift
		otRequest.value.punch_ot_hours = data.punch_ot_hours
		otRequest.value.compensation = data.compensation

		const claimedField = formFields.data.find((f) => f.fieldname === "claimed_hours")
		if (claimedField) {
			claimedField.description = data.punch_ot_hours
				? __("Punch-verified maximum: {0} h", [data.punch_ot_hours])
				: ""
		}
		// re-validate against the freshly loaded cap — the claimed_hours watcher
		// does not fire when the summary lands.
		validateClaimedHours()
	},
	onError() {
		console.warn("[OTRequestForm] Failed to fetch OT summary:", otRequest.value.ot_date)
	},
})

watch(
	() => otRequest.value.ot_date,
	(ot_date) => {
		if (!ot_date || props.id) return
		otSummary.fetch({ employee: employee.data.name, date: ot_date })
	}
)

function validateClaimedHours() {
	const claimedField = formFields.data?.find((f) => f.fieldname === "claimed_hours")
	if (!claimedField) return
	// punch_ot_hours is set only once the summary loads. Guard on == null (NOT
	// truthiness): a real 0 cap (no OT punched that day) is falsy, so the old
	// `claimed && cap &&` skipped the block AND cleared the "nothing to claim"
	// error the summary set — letting the claim through to a server rejection.
	const cap = otRequest.value.punch_ot_hours
	const claimed = Number(otRequest.value.claimed_hours || 0)
	if (cap == null) {
		claimedField.error_message = ""
	} else if (cap === 0) {
		claimedField.error_message = __("No punch-verified overtime for this date — nothing to claim")
	} else if (claimed > cap) {
		claimedField.error_message = __("Cannot claim more than the punch-verified {0} h", [cap])
	} else {
		claimedField.error_message = ""
	}
}

watch(() => otRequest.value.claimed_hours, validateClaimedHours)

watch(
	() => otRequest.value.employee,
	(employee_id) => {
		if (props.id && employee_id && employee_id !== employee.data.name) {
			formFields.data.map((field) => (field.read_only = true))
		}
	}
)

function validateForm() {
	otRequest.value.employee = employee.data.name
}
</script>
