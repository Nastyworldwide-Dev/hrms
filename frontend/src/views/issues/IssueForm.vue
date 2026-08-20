<template>
	<GPage>
		<ion-content :fullscreen="true">
			<FormView
				v-if="formFields.data"
				doctype="Employee Issue"
				v-model="issue"
				:isSubmittable="false"
				:fields="formFields.data"
				:id="props.id"
				:showAttachmentView="true"
				@validateForm="validateForm"
			/>
			<ResourceError :resource="formFields" what="the issue form" />
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

const props = defineProps({
	id: {
		type: String,
		required: false,
	},
})

const issue = ref({})

// identity is auto-filled server-side from the session employee; status and
// HR-internal fields never render in the employee-facing form
const HIDDEN_ON_CREATE = [
	"employee",
	"employee_name",
	"department",
	"column_break_emp",
	"company",
	"column_break_issue",
	"status",
	"hr_section",
	"hr_notes",
]
const HR_ONLY_FIELDS = ["hr_section", "hr_notes"]
const LEAVE_FIELDS = ["leave_section", "leave_type", "balance_shown", "balance_expected", "column_break_leave"]
const ATTENDANCE_FIELDS = ["attendance_section", "affected_date", "punch_affected", "column_break_att", "what_happened"]

const formFields = createResource({
	url: "hrms.api.get_doctype_fields",
	params: { doctype: "Employee Issue" },
	auto: true,
	transform(data) {
		let fields = data.filter((field) => !HR_ONLY_FIELDS.includes(field.fieldname))
		if (!props.id) {
			fields = fields.filter((field) => !HIDDEN_ON_CREATE.includes(field.fieldname))
			applyConditionalSections(fields, issue.value.issue_type)
		} else {
			// tickets are read-only in the PWA once filed — HR works the board
			fields.map((field) => (field.read_only = true))
		}
		return fields
	},
})

const applyConditionalSections = (fields, issueType) => {
	console.info("[IssueForm] toggling conditional sections for:", issueType)
	const showLeave = issueType === "Leave Balance Discrepancy"
	const showAttendance = issueType === "Check-in / Check-out Problem"
	fields.forEach((field) => {
		if (LEAVE_FIELDS.includes(field.fieldname)) field.hidden = !showLeave
		if (ATTENDANCE_FIELDS.includes(field.fieldname)) field.hidden = !showAttendance
	})
}

watch(
	() => issue.value.issue_type,
	(issueType) => {
		// runs on detail views too, once FormView loads the doc — a leave
		// ticket shouldn't render the empty attendance section
		if (!formFields.data) return
		applyConditionalSections(formFields.data, issueType)
	}
)

function validateForm() {
	issue.value.employee = employee.data.name
}
</script>
