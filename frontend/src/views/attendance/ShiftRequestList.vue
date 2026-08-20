<template>
	<GPage>
		<ListView
			doctype="Shift Request"
			pageTitle="Shift Request History"
			:tabButtons="TAB_BUTTONS"
			:fields="SHIFT_REQUEST_FIELDS"
			:filterConfig="FILTER_CONFIG"
		/>
	</GPage>
</template>

<script setup>
import GPage from "@/components/glass/GPage.vue"
import { inject } from "vue"
import ListView from "@/components/ListView.vue"

const __ = inject("$translate")
const TAB_BUTTONS = ["My Requests", "Team Requests"]
const SHIFT_REQUEST_FIELDS = [
	"name",
	"employee",
	"employee_name",
	"shift_type",
	"from_date",
	"to_date",
	"approver",
	"status",
	"docstatus",
]
const STATUS_FILTER_OPTIONS = ["Draft", "Approved", "Rejected"]
const FILTER_CONFIG = [
	{
		fieldname: "status",
		fieldtype: "Select",
		label: __("Status"),
		options: STATUS_FILTER_OPTIONS,
	},
	{
		fieldname: "shift_type",
		fieldtype: "Link",
		label: __("Shift Type"),
		options: "Shift Type",
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
	{ fieldname: "from_date", fieldtype: "Date", label: __("From Date") },
	{ fieldname: "to_date", fieldtype: "Date", label: __("To Date") },
]
</script>
