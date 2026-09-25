<template>
	<GPage>
		<ion-content :fullscreen="true">
			<FormView
				v-if="formFields.data"
				doctype="Leave Application"
				:noun="__('leave request')"
				v-model="leaveApplication"
				:isSubmittable="true"
				:fields="formFields.data"
				:id="props.id"
				:showAttachmentView="true"
				@validateForm="validateForm"
			>
				<!-- What the chosen half means, in the person's own shift, under the
				     group that asks it (owner, 25 Sep 2026: clear, no confusion). -->
				<template #groupFooter="{ group }">
					<p
						v-if="leaveApplication.half_day && groupHasSession(group)"
						class="g-form-footer g-halfday-note"
						role="status"
					>
						{{ sessionGuidance(halfDayHints.data, leaveApplication.half_day_session, __) }}
					</p>
				</template>
			</FormView>
			<ResourceError :resource="formFields" back what="the leave application form" />
		</ion-content>
	</GPage>
</template>

<script setup>
import { approverOptions } from "@/utils/approverOptions"
import GPage from "@/components/glass/GPage.vue"
import { IonContent } from "@ionic/vue"
import { createResource } from "frappe-ui"
import { gToast } from "@/components/glass/toast"
import { ref, watch, inject, nextTick } from "vue"
import { useRoute } from "vue-router"

import { dateFromRoute } from "@/utils/dateFromRoute"
import { sessionGuidance, sessionOptions } from "@/utils/halfDaySession"

import FormView from "@/components/FormView.vue"
import { firstMessage } from "@/utils/loudRequest"

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

// reactive object to store form data. A Calendar day's "Ask for this day off"
// opens on that day (?date=, 01-calendar.md §4 row 13).
const route = useRoute()
const startDay = props.id ? null : dateFromRoute(route.query)
const leaveApplication = ref(startDay ? { from_date: startDay, to_date: startDay } : {})

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
			// Asked only for a half day, and each choice says what it means in
			// the person's shift (owner, 25 Sep 2026).
			if (field.fieldname === "half_day_session") {
				field.label = __("Which half")
				field.hidden = !leaveApplication.value.half_day
				field.documentList = sessionOptions(null, __)
			}

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
	onError(error) {
		// without this, a failed fetch leaves the dropdown as a silent
		// "No results found" that reads like the employee has no leave
		console.warn(
			"[LeaveForm] Failed to fetch leave types:",
			currEmployee.value,
			firstMessage(error)
		)
		gToast({
			title: __("Error"),
			text: __("Could not load leave types: {0}. Please contact HR.", [firstMessage(error)]),
			variant: "error",
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

//: The fields this screen asks for, in the doctype's own order.
//:
//: An ALLOWLIST, replacing the `excludeFields` blacklist. A blacklist decides
//: what to hide, so anything it has not heard of is shown — and it is a
//: snapshot of the schema on the day somebody wrote it, while the schema keeps
//: growing. Read against the running site, the old list was letting through
//: `synced_from_instance` (this app's cross-instance mirror flag), `color` (a
//: Desk calendar colour) and `amended_from` (Frappe's link to the cancelled
//: document this one replaced). None is a question to ask somebody booking
//: time off; none was deliberately allowed.
//:
//: Adding a field to this screen is now a deliberate act, and a migration
//: cannot leak one by itself.
const FIELDS = [
	"leave_type",
	"from_date",
	"to_date",
	"half_day",
	"half_day_session",
	"half_day_date",
	"total_leave_days",
	"description",
	"leave_balance",
	"leave_approver",
	"leave_approver_name",
]

//: Shown only when READING an existing application — on a new one they are
//: filled from the session, and asking is noise. Same split the blacklist made,
//: kept deliberately.
const FIELDS_ON_EXISTING = [
	"employee",
	"employee_name",
	"department",
	"company",
	"status",
	"posting_date",
]

//: Layout, kept by KIND rather than by name. These are called
//: `section_break_5` and `column_break_18` — generated names that change the
//: moment somebody reorders the doctype in Desk, so naming them would be a
//: list that breaks on a layout edit.
const LAYOUT = ["Section Break", "Column Break", "Tab Break"]

function getFilteredFields(fields) {
	const wanted = props.id ? [...FIELDS, ...FIELDS_ON_EXISTING] : FIELDS
	return fields.filter(
		(field) => wanted.includes(field.fieldname) || LAYOUT.includes(field.fieldtype)
	)
}

function setFormReadOnly() {
	if (leaveApplication.value.leave_approver === sessionEmployee.data.user_id) return
	formFields.data.map((field) => (field.read_only = true))
}

function validateDates(from_date, to_date) {
	if (!(from_date && to_date)) return

	const error_message =
		from_date > to_date ? __("The end date cannot be before the start date") : ""

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

//: The group that holds the AM | PM row carries the guidance line.
const groupHasSession = (group) =>
	group.segments.some((seg) => seg.fields?.some((f) => f.fieldname === "half_day_session"))

//: What AM and PM mean on the half-day date, in the caller's own shift.
const halfDayHints = createResource({
	url: "hrms.api.half_day.get_half_day_hints",
	onSuccess(hints) {
		const session = formFields.data?.find((field) => field.fieldname === "half_day_session")
		if (session) session.documentList = sessionOptions(hints, __)
	},
	onError(error) {
		// the plain options stay; the choice is still clear without the clock
		console.warn("[LeaveForm] half-day hints unavailable:", firstMessage(error))
	},
})

watch(
	() => leaveApplication.value.half_day && leaveApplication.value.half_day_date,
	(day) => {
		if (day) halfDayHints.submit({ day: leaveApplication.value.half_day_date })
	}
)

function setHalfDayDate(half_day) {
	const session = formFields.data.find((field) => field.fieldname === "half_day_session")
	if (session) {
		session.hidden = !half_day
		session.reqd = Boolean(half_day)
		if (!half_day) leaveApplication.value.half_day_session = ""
	}
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
	// Nobody chooses their approver (owner, 25 Sep 2026): the row shows their
	// own, read-only; the server sets it whatever is sent.
	leave_approver.documentList = approverOptions(data?.department_approvers).slice(0, 1)
	leave_approver.read_only = 1
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
