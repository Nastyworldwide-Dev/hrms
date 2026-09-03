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
				:requireAttachment="false"
				@validateForm="validateForm"
			/>
			<ResourceError :resource="formFields" back what="the replacement leave claim form" />
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
				"{0} banked hours available to claim — 0.5 day costs 4 h, 1 day costs 8 h",
				[data.hours_available]
			)
		// re-check now that the cap is known — the days watcher does not fire when
		// the bank loads, so a claim typed before it arrived stayed unvalidated.
		validateClaimedDays()
	},
	onError() {
		console.warn("[ReplacementLeaveClaimForm] Failed to fetch bank summary")
	},
})

function validateClaimedDays() {
	const daysField = formFields.data?.find((f) => f.fieldname === "claimed_days")
	if (!daysField) return
	const numeric = Number(claim.value.claimed_days || 0)
	const cost = numeric * 8
	claim.value.hours_cost = cost
	// available_hours is set only once the bank summary loads. Guard on != null,
	// NOT truthiness: a real 0-hours bank (nothing banked — the MOST invalid
	// case) is falsy, so `&& available_hours &&` silently skipped the block and
	// let the claim through to a server rejection + a stack of error toasts.
	const available = claim.value.available_hours
	if (numeric && (numeric * 2) % 1 !== 0) {
		daysField.error_message = __("Days must be in half-day steps (0.5, 1.0, 1.5 ...)")
	} else if (cost && available != null && cost > available) {
		daysField.error_message = __("Costs {0} h — only {1} h banked and claimable", [
			cost,
			available,
		])
	} else {
		daysField.error_message = ""
	}
}

watch(() => claim.value.claimed_days, validateClaimedDays)

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
