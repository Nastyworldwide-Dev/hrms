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
import { ref, watch, inject } from "vue"

import FormView from "@/components/FormView.vue"

const employee = inject("$employee")
const __ = inject("$translate")

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
			(field) =>
				!["employee", "employee_name", "department", "company", "status"].includes(field.fieldname)
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
