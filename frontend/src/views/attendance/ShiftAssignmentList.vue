<template>
	<GPage>
		<ListView
			doctype="Shift Assignment"
			:pageTitle="__('Shift Assignment History')"
			:fields="SHIFT_ASSIGNMENT_FIELDS"
			:filterConfig="FILTER_CONFIG"
		/>
	</GPage>
</template>

<script setup>
import GPage from "@/components/glass/GPage.vue"
import { inject } from "vue"
import ListView from "@/components/ListView.vue"

const __ = inject("$translate")

const SHIFT_ASSIGNMENT_FIELDS = ["name", "shift_type", "start_date", "end_date", "docstatus"]
const FILTER_CONFIG = [
	{
		fieldname: "shift_type",
		fieldtype: "Link",
		label: __("Shift Type"),
		options: "Shift Type",
	},
	{ fieldname: "start_date", fieldtype: "Date", label: __("Start Date") },
	{ fieldname: "end_date", fieldtype: "Date", label: __("End Date") },
]
</script>
