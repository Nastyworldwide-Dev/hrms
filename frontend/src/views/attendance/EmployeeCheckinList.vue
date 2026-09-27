<template>
	<GPage>
		<ListView
			doctype="Employee Checkin"
			:pageTitle="__('Check-ins')"
			:fields="EMPLOYEE_CHECKIN_FIELDS"
			:filterConfig="FILTER_CONFIG"
			orderBy="time desc"
		/>
	</GPage>
</template>

<script setup>
import { inject } from "vue"
import GPage from "@/components/glass/GPage.vue"
import ListView from "@/components/ListView.vue"

const __ = inject("$translate")

// shift_start: the work day a tap counts on (utils/dayGroups workDayOf)
// and what the check-in sheet shows (alpha.14 A): where in words, the photo,
// the quiet coordinates
const EMPLOYEE_CHECKIN_FIELDS = [
	"name",
	"log_type",
	"time",
	"shift_start",
	"latitude",
	"longitude",
	"geofence_outcome",
	"geofence_distance_m",
	"location_accuracy_m",
	"selfie_image",
]

const FILTER_CONFIG = [
	{
		fieldname: "log_type",
		fieldtype: "Select",
		label: __("Check-in type"),
		options: "IN\nOUT",
	},
	{
		fieldname: "shift",
		fieldtype: "Link",
		label: __("Shift"),
		options: "Shift Type",
	},
]
</script>
