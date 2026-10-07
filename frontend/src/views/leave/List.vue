<template>
	<GPage>
		<ListView
			doctype="Leave Application"
			:pageTitle="__('Time off')"
			:fields="LEAVE_FIELDS"
			:filterConfig="FILTER_CONFIG"
		/>
	</GPage>
</template>

<script setup>
import GPage from "@/components/glass/GPage.vue"
import ListView from "@/components/ListView.vue"
import { inject } from "vue"
import { requestStatus } from "@/utils/requestStatus"

const __ = inject("$translate")
const LEAVE_FIELDS = [
	"name",
	"employee",
	"employee_name",
	"leave_type",
	"from_date",
	"to_date",
	"total_leave_days",
	"status",
]
// The filter SHOWS the word a row's chip shows and SENDS the stored value
// (the DB still says "Open"). The label comes from the chip's own rule, so the
// two cannot drift; FormField translates it.
const stateOption = (value, docstatus) => ({
	label: requestStatus("Leave Application", { status: value, docstatus }).label,
	value,
})
const STATUS_FILTER_OPTIONS = [
	stateOption("Open", 0),
	stateOption("Approved", 1),
	stateOption("Rejected", 1),
]
const FILTER_CONFIG = [
	{
		fieldname: "status",
		fieldtype: "Select",
		label: __("Status"),
		options: STATUS_FILTER_OPTIONS,
	},
	{
		fieldname: "leave_type",
		fieldtype: "Link",
		label: __("Leave type"),
		options: "Leave Type",
	},
	{
		fieldname: "employee",
		fieldtype: "Link",
		label: __("Employee"),
		options: "Employee",
	},
	{
		fieldname: "department",
		fieldtype: "Link",
		label: __("Department"),
		options: "Department",
	},
	{ fieldname: "from_date", fieldtype: "Date", label: __("From date") },
	{ fieldname: "to_date", fieldtype: "Date", label: __("To date") },
]
</script>
