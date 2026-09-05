<template>
	<GPage>
		<ion-content :fullscreen="true">
			<FormView
				v-if="formFields.data"
				doctype="Attendance Request"
				v-model="attendanceRequest"
				:isSubmittable="true"
				:fields="formFields.data"
				:id="props.id"
				:showAttachmentView="true"
				:requireAttachment="false"
				@validateForm="validateForm"
			/>
			<ResourceError :resource="formFields" back what="the attendance request form" />
		</ion-content>
	</GPage>
</template>

<script setup>
import GPage from "@/components/glass/GPage.vue"
import { IonContent } from "@ionic/vue"
import { createResource } from "frappe-ui"
import { ref, watch, inject } from "vue"

import FormView from "@/components/FormView.vue"
import { shiftTypes } from "@/data/attendance"

const employee = inject("$employee")
const __ = inject("$translate")

const props = defineProps({
	id: {
		type: String,
		required: false,
	},
})

// reactive object to store form data
const attendanceRequest = ref({})

// get form fields
const formFields = createResource({
	url: "hrms.api.get_doctype_fields",
	params: { doctype: "Attendance Request" },
	auto: true,
	transform(data) {
		if (props.id) return data
		return data.filter(
			(field) => !["employee", "employee_name", "status", "company"].includes(field.fieldname)
		)
	},
})

// shift is an optional Link to the Shift Type master; rendered raw it searches via
// search_link, which a bare Employee can't use, so the picker came up empty. Feed the
// fenced list as a documentList (FormView forwards it to the field).
function applyShiftTypeOptions() {
	const field = formFields.data?.find((f) => f.fieldname === "shift")
	if (!field || !shiftTypes.data) return
	field.documentList = shiftTypes.data.map((t) => ({ label: t.name, value: t.name }))
}
watch([() => formFields.data, () => shiftTypes.data], applyShiftTypeOptions, { immediate: true })

// form scripts
watch(
	() => attendanceRequest.value.employee,
	(employee_id) => {
		if (props.id && employee_id !== employee.data.name) {
			// if employee is not the current user, set form as read only
			setFormReadOnly()
		}
	}
)

watch(
	() => attendanceRequest.value.from_date,
	(from_date) => {
		if (!attendanceRequest.value.to_date) {
			attendanceRequest.value.to_date = from_date
		}
	}
)

watch(
	() => [attendanceRequest.value.from_date, attendanceRequest.value.to_date],
	([from_date, to_date]) => {
		validateDates(from_date, to_date)
	}
)

watch(
	() => attendanceRequest.value.half_day,
	(half_day) => {
		const half_day_date = formFields.data.find((field) => field.fieldname === "half_day_date")
		half_day_date.hidden = !half_day
	}
)

watch(
	() => [attendanceRequest.value.in_time, attendanceRequest.value.out_time],
	([in_time, out_time]) => {
		const out_time_field = formFields.data.find((field) => field.fieldname === "out_time")
		if (!out_time_field) return
		out_time_field.error_message =
			!!in_time !== !!out_time ? __("Both In Time and Out Time are required") : ""
	}
)

// helper functions
function setFormReadOnly() {
	formFields.data.map((field) => (field.read_only = true))
}

function validateDates(from_date, to_date) {
	if (!(from_date && to_date)) return

	const error_message = from_date > to_date ? __("To Date cannot be before From Date") : ""

	const from_date_field = formFields.data.find((field) => field.fieldname === "from_date")
	from_date_field.error_message = error_message
}

function validateForm() {
	attendanceRequest.value.employee = employee.data.name
}
</script>
