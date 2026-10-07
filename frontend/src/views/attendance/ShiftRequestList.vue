<template>
	<GPage>
		<ListView
			doctype="Shift Request"
			:pageTitle="__('Shift changes')"
			:fields="SHIFT_REQUEST_FIELDS"
			:filterConfig="FILTER_CONFIG"
		/>
	</GPage>
</template>

<script setup>
import GPage from "@/components/glass/GPage.vue"
import { inject } from "vue"
import ListView from "@/components/ListView.vue"
import { requestStatus } from "@/utils/requestStatus"

const __ = inject("$translate")
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
// The filter SHOWS the word a row's chip shows and SENDS the stored value
// (the DB still says "Draft"). The label comes from the chip's own rule, so the
// two cannot drift; FormField translates it.
const stateOption = (value, docstatus) => ({
	label: requestStatus("Shift Request", { status: value, docstatus }).label,
	value,
})
const STATUS_FILTER_OPTIONS = [
	stateOption("Draft", 0),
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
		fieldname: "shift_type",
		fieldtype: "Link",
		label: __("Shift type"),
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
	{ fieldname: "from_date", fieldtype: "Date", label: __("From date") },
	{ fieldname: "to_date", fieldtype: "Date", label: __("To date") },
]
</script>
