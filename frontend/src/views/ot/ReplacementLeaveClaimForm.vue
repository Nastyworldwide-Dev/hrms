<template>
	<GPage>
		<ion-content :fullscreen="true">
			<FormView
				v-if="formFields.data"
				doctype="Replacement Leave Claim"
				v-model="claim"
				:isSubmittable="true"
				:fields="formFields.data"
				:id="props.id"
				:showAttachmentView="true"
				:requireAttachment="true"
				@validateForm="validateForm"
			/>
			<ResourceError :resource="formFields" what="the replacement leave claim form" />
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

const claim = ref({})

const formFields = createResource({
	url: "hrms.api.get_doctype_fields",
	params: { doctype: "Replacement Leave Claim" },
	auto: true,
	transform(data) {
		if (props.id) return data
		return data.filter(
			(field) =>
				![
					"employee",
					"employee_name",
					"department",
					"company",
					// decision shown on detail, never offered on create
					"status",
					"bank_month",
					"leave_type",
					"leave_allocation",
				].includes(field.fieldname)
		)
	},
	onSuccess() {
		if (!props.id) bank.fetch({ employee: employee.data.name })
	},
})

const bank = createResource({
	url: "hrms.api.get_replacement_leave_bank_summary",
	onSuccess(data) {
		claim.value.available_hours = data.hours_available
		const daysField = formFields.data.find((f) => f.fieldname === "claimed_days")
		if (daysField)
			daysField.description = __(
				"{0} banked hours available this month — 0.5 day costs 4 h, 1 day costs 8 h",
				[data.hours_available]
			)
	},
	onError() {
		console.warn("[ReplacementLeaveClaimForm] Failed to fetch bank summary")
	},
})

watch(
	() => claim.value.claimed_days,
	(days) => {
		const daysField = formFields.data?.find((f) => f.fieldname === "claimed_days")
		if (!daysField) return
		const numeric = Number(days || 0)
		const cost = numeric * 8
		claim.value.hours_cost = cost
		if (numeric && (numeric * 2) % 1 !== 0) {
			daysField.error_message = __("Days must be in half-day steps (0.5, 1.0, 1.5 ...)")
		} else if (cost && claim.value.available_hours && cost > claim.value.available_hours) {
			daysField.error_message = __("Costs {0} h — only {1} h banked this month", [
				cost,
				claim.value.available_hours,
			])
		} else {
			daysField.error_message = ""
		}
	}
)

watch(
	() => claim.value.employee,
	(employee_id) => {
		if (props.id && employee_id && employee_id !== employee.data.name) {
			formFields.data.map((field) => (field.read_only = true))
		}
	}
)

function validateForm() {
	claim.value.employee = employee.data.name
}
</script>
