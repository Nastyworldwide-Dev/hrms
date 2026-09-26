<template>
	<GPage>
		<ListView
			doctype="OT Request"
			:pageTitle="__('Overtime')"
			:fields="OT_REQUEST_FIELDS"
			:filterConfig="FILTER_CONFIG"
		/>
	</GPage>
</template>

<script setup>
import GPage from "@/components/glass/GPage.vue"
import ListView from "@/components/ListView.vue"
import { inject } from "vue"

const __ = inject("$translate")

const OT_REQUEST_FIELDS = [
	"name",
	"ot_date",
	"claimed_hours",
	"compensation",
	"docstatus",
	"status",
]
const FILTER_CONFIG = [
	// "OT Date" is a fieldname with a space in it, and "Compensation" is the
	// field's label in Desk. The questions underneath them are "when?" and
	// "paid, or a day off?" — which is what the two options already answer, so
	// the label can simply ask it (2.0 slice 2.2).
	//
	// The OPTIONS keep the server's spelling: they are the doctype's Select
	// values and the filter sends them as-is. What a row DISPLAYS is a separate
	// question, answered in OTRequestItem.
	{ fieldname: "ot_date", fieldtype: "Date", label: __("Date worked") },
	{
		fieldname: "compensation",
		fieldtype: "Select",
		label: __("Paid or time off"),
		options: "\nOvertime Pay\nReplacement Leave",
	},
]
</script>
