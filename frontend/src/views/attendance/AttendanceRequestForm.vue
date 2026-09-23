<template>
	<GPage>
		<ion-content :fullscreen="true">
			<FormView
				v-if="formFields.data"
				doctype="Attendance Request"
				:noun="__('attendance request')"
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
import { useRoute } from "vue-router"

import { dateFromRoute } from "@/utils/dateFromRoute"

import FormView from "@/components/FormView.vue"

const employee = inject("$employee")
const __ = inject("$translate")

const props = defineProps({
	id: {
		type: String,
		required: false,
	},
})

// reactive object to store form data. A Calendar day's "Fix this day" opens
// with that day chosen (?date=, approved Calendar plan D2).
const route = useRoute()
const startDay = props.id ? null : dateFromRoute(route.query)
const attendanceRequest = ref(startDay ? { from_date: startDay, to_date: startDay } : {})

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
			!!in_time !== !!out_time ? __("Give both the time in and the time out") : ""
	}
)

// helper functions
function setFormReadOnly() {
	formFields.data.map((field) => (field.read_only = true))
}

function validateDates(from_date, to_date) {
	if (!(from_date && to_date)) return

	const error_message =
		from_date > to_date ? __("The end date cannot be before the start date") : ""

	const from_date_field = formFields.data.find((field) => field.fieldname === "from_date")
	from_date_field.error_message = error_message
}

function validateForm() {
	attendanceRequest.value.employee = employee.data.name
}
</script>
