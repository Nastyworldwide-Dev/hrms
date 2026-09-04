<template>
	<GPage>
		<ListView
			doctype="Employee Checkin"
			:pageTitle="__('Employee Checkin History')"
			:fields="EMPLOYEE_CHECKIN_FIELDS"
			:filterConfig="FILTER_CONFIG"
			orderBy="time desc"
		/>
	</GPage>
</template>

<script setup>
import { inject } from "vue";
import GPage from "@/components/glass/GPage.vue";
import ListView from "@/components/ListView.vue";

const __ = inject("$translate");

const EMPLOYEE_CHECKIN_FIELDS = [
	"name",
	"log_type",
	"time",
	"latitude",
	"longitude",
];

const FILTER_CONFIG = [
	{
		fieldname: "log_type",
		fieldtype: "Select",
		label: __("Log Type"),
		options: "IN\nOUT",
	},
	{
		fieldname: "shift",
		fieldtype: "Link",
		label: __("Shift"),
		options: "Shift Type",
	},
];
</script>
