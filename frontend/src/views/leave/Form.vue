<template>
	<GPage>
		<ion-content :fullscreen="true">
			<FormView
				v-if="formFields.data"
				doctype="Leave Application"
				v-model="leaveApplication"
				:isSubmittable="true"
				:fields="formFields.data"
				:id="props.id"
				:showAttachmentView="true"
				@validateForm="validateForm"
			/>
			<ResourceError :resource="formFields" what="the leave application form" />
		</ion-content>
	</GPage>
</template>

<script setup>
import GPage from "@/components/glass/GPage.vue"
import { IonContent } from "@ionic/vue"
import { createResource, toast } from "frappe-ui"
import { ref, watch, inject, nextTick } from "vue"

import FormView from "@/components/FormView.vue"

const dayjs = inject("$dayjs")
const __ = inject("$translate")
const today = dayjs().format("YYYY-MM-DD")

const props = defineProps({
	id: {
		type: String,
		required: false,
	},
})

const sessionEmployee = inject("$employee")
const currEmployee = ref(sessionEmployee.data.name)

// reactive object to store form data
const leaveApplication = ref({})

// For existing docs, watchers fire during initial data population from the DB.
// This flag prevents setLeaveBalance() from overwriting the stored
// "leave balance before application" value during that initial load.
const isFormInitialized = ref(!props.id)
if (props.id) {
	watch(
		() => leaveApplication.value.name,
		(name) => {
			if (name && !isFormInitialized.value) {
				nextTick(() => {
					isFormInitialized.value = true
				})
			}
		}
	)
}

// get form fields
const formFields = createResource({
	url: "hrms.api.get_doctype_fields",
	params: { doctype: "Leave Application" },
	transform(data) {
		let fields = getFilteredFields(data)

		return fields.map((field) => {
			if (field.fieldname === "half_day_date") field.hidden = true

			if (field.fieldname === "posting_date") field.default = today

			return field
		})
	},
	onSuccess(_data) {
		leaveApprovalDetails.reload()
		leaveTypes.reload()
	},
})
formFields.reload()

const leaveApprovalDetails = createResource({
	url: "hrms.api.get_leave_approval_details",
	params: { employee: currEmployee.value },
	onSuccess(data) {
		setLeaveApprovers(data)
	},
})

const leaveTypes = createResource({
	url: "hrms.api.get_leave_types",
	params: {
		employee: currEmployee.value,
		date: today,
	},
	onSuccess(data) {
		setLeaveTypes(data)
	},
	onError() {
		// without this, a failed fetch leaves the dropdown as a silent
		// "No results found" that reads like the employee has no leave
		console.warn("[LeaveForm] Failed to fetch leave types:", currEmployee.value)
		toast({
			title: __("Error"),
			text: __("Could not load leave types. Please contact HR."),
			icon: "alert-circle",
			position: "bottom-center",
			iconClasses: "text-red-500",
		})
	},
})

// form scripts
watch(
	() => leaveApplication.value.employee,
	(employee_id) => {
		// the form model is transiently empty across save/reload cycles —
		// refetching with a blank employee 404s and toasts "Could not load
		// leave types" once per cycle
		if (!employee_id) return

		if (props.id && employee_id !== currEmployee.value) {
			// if employee is not the current user, set form as read only
			setFormReadOnly()
		}
		currEmployee.value = employee_id
		leaveTypes.fetch({ employee: currEmployee.value, date: today })
		leaveApprovalDetails.fetch({ employee: currEmployee.value })
	}
)
watch(
	() => leaveApplication.value.leave_type,
	(leave_type) => setLeaveBalance(leave_type)
)

watch(
	() => leaveApplication.value.half_day,
	(half_day) => setHalfDayDate(half_day)
)

watch(
	() => leaveApplication.value.half_day && leaveApplication.value.half_day_date,
	() => {
		setTotalLeaveDays()
		validateHalfDayDate()
	}
)

watch(
	() => leaveApplication.value.from_date,
	(from_date) => {
		if (!leaveApplication.value.to_date) {
			leaveApplication.value.to_date = from_date
		}

		// fetch leave types for the selected date
		leaveTypes.fetch({
			employee: currEmployee.value,
			date: from_date,
		})
	}
)

watch(
	() => [leaveApplication.value.from_date, leaveApplication.value.to_date],
	([from_date, to_date]) => {
		validateDates(from_date, to_date)
		setHalfDayDateRange()
		validateHalfDayDate()
		setTotalLeaveDays()
	}
)

watch(
	() => leaveApplication.value.leave_approver,
	(newApprover) => {
		const approverField = formFields.data.find((f) => f.fieldname === "leave_approver")
		const selected = approverField?.documentList?.find((opt) => opt.value === newApprover)
		leaveApplication.value.leave_approver_name = selected?.label?.split(" : ")[1] || ""
	}
)

// helper functions
function getFilteredFields(fields) {
	// reduce noise from the form view by excluding unnecessary fields
	// ex: employee and other details can be fetched from the session user
	const excludeFields = ["naming_series", "sb_other_details", "salary_slip", "letter_head"]

	const employeeFields = [
		"employee",
		"employee_name",
		"department",
		"company",
		"follow_via_email",
		"status",
		"posting_date",
	]

	if (!props.id) excludeFields.push(...employeeFields)

	return fields.filter((field) => !excludeFields.includes(field.fieldname))
}

function setFormReadOnly() {
	if (leaveApplication.value.leave_approver === sessionEmployee.data.user_id) return
	formFields.data.map((field) => (field.read_only = true))
}

function validateDates(from_date, to_date) {
	if (!(from_date && to_date)) return

	const error_message = from_date > to_date ? __("To Date cannot be before From Date") : ""

	const from_date_field = formFields.data.find((field) => field.fieldname === "from_date")
	from_date_field.error_message = error_message
}

function validateHalfDayDate() {
	// frappe-ui's DatePicker can't constrain its own min/max, so the half-day
	// date could be picked outside the leave range and only the server caught
	// it. Enforce it through the error_message channel the form blocks submit on.
	const field = formFields.data.find((f) => f.fieldname === "half_day_date")
	if (!field) return
	const { half_day, half_day_date, from_date, to_date } = leaveApplication.value
	const outOfRange =
		half_day &&
		half_day_date &&
		from_date &&
		to_date &&
		(half_day_date < from_date || half_day_date > to_date)
	field.error_message = outOfRange ? __("Half day date must fall within the leave dates") : ""
}

function setTotalLeaveDays() {
	if (!areValuesSet()) return

	const leaveDays = createResource({
		url: "hrms.hr.doctype.leave_application.leave_application.get_number_of_leave_days",
		params: {
			employee: currEmployee.value,
			leave_type: leaveApplication.value.leave_type,
			from_date: leaveApplication.value.from_date,
			to_date: leaveApplication.value.to_date,
			half_day: leaveApplication.value.half_day,
			half_day_date: leaveApplication.value.half_day_date,
		},
		onSuccess(data) {
			leaveApplication.value.total_leave_days = data
		},
	})
	leaveDays.reload()
	setLeaveBalance()
}

function setLeaveBalance() {
	if (!areValuesSet()) return
	if (!isFormInitialized.value) return

	const leaveBalance = createResource({
		url: "hrms.hr.doctype.leave_application.leave_application.get_leave_balance_on",
		params: {
			employee: currEmployee.value,
			date: leaveApplication.value.from_date,
			to_date: leaveApplication.value.to_date,
			leave_type: leaveApplication.value.leave_type,
			consider_all_leaves_in_the_allocation_period: 1,
		},
		onSuccess(data) {
			leaveApplication.value.leave_balance = data
		},
	})
	leaveBalance.reload()
}

function setHalfDayDate(half_day) {
	const half_day_date = formFields.data.find((field) => field.fieldname === "half_day_date")
	half_day_date.hidden = !half_day
	half_day_date.reqd = half_day

	if (!half_day) return

	if (leaveApplication.value.from_date === leaveApplication.value.to_date) {
		leaveApplication.value.half_day_date = leaveApplication.value.from_date
	} else {
		setHalfDayDateRange()
	}
}

function setHalfDayDateRange() {
	const half_day_date = formFields.data.find((field) => field.fieldname === "half_day_date")
	half_day_date.minDate = leaveApplication.value.from_date
	half_day_date.maxDate = leaveApplication.value.to_date
}

function setLeaveApprovers(data) {
	const leave_approver = formFields.data?.find((field) => field.fieldname === "leave_approver")
	leave_approver.reqd = data?.is_mandatory
	leave_approver.documentList = data?.department_approvers.map((approver) => ({
		label: approver.full_name ? `${approver.name} : ${approver.full_name}` : approver.name,
		value: approver.name,
	}))
	if (!leaveApplication.value.leave_approver) {
		leaveApplication.value.leave_approver = data?.leave_approver
		leaveApplication.value.leave_approver_name = data?.leave_approver_name
	}
}

function setLeaveTypes(data) {
	const leave_type = formFields.data.find((field) => field.fieldname === "leave_type")
	leave_type.documentList = data?.map((leave_type) => ({
		label: leave_type,
		value: leave_type,
	}))
}

function areValuesSet() {
	return (
		leaveApplication.value.from_date &&
		leaveApplication.value.to_date &&
		leaveApplication.value.leave_type
	)
}

function validateForm() {
	setHalfDayDate(leaveApplication.value.half_day)
	leaveApplication.value.employee = currEmployee.value
}
</script>
