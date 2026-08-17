<template>
	<ion-page>
		<ion-content :fullscreen="true">
			<FormView
				v-if="formFields.data"
				doctype="OT Request"
				v-model="otRequest"
				:isSubmittable="true"
				:fields="formFields.data"
				:id="props.id"
				:showAttachmentView="true"
				:requireAttachment="true"
				@validateForm="validateForm"
			/>
			<ResourceError :resource="formFields" what="the overtime request form" />
		</ion-content>
	</ion-page>
</template>

<script setup>
import { IonPage, IonContent } from "@ionic/vue"
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
			(field) =>
				!["employee", "employee_name", "department", "company"].includes(field.fieldname)
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
		if (!claimedField) return
		if (!data.punch_ot_hours) {
			claimedField.error_message = __(
				"No punch-verified overtime for this date — nothing to claim"
			)
		} else {
			claimedField.error_message = ""
			claimedField.description = __("Punch-verified maximum: {0} h", [data.punch_ot_hours])
		}
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

watch(
	() => otRequest.value.claimed_hours,
	(claimed) => {
		const claimedField = formFields.data?.find((f) => f.fieldname === "claimed_hours")
		if (!claimedField) return
		const cap = otRequest.value.punch_ot_hours || 0
		claimedField.error_message =
			claimed && cap && Number(claimed) > cap
				? __("Cannot claim more than the punch-verified {0} h", [cap])
				: ""
	}
)

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
