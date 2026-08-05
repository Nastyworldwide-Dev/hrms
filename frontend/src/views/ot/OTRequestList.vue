<template>
	<ion-page>
		<ListView
			doctype="OT Request"
			:pageTitle="__('OT Request History')"
			:fields="OT_REQUEST_FIELDS"
			:filterConfig="FILTER_CONFIG"
		/>
	</ion-page>
</template>

<script setup>
import { IonPage } from "@ionic/vue"
import ListView from "@/components/ListView.vue"
import { inject } from "vue"

const __ = inject("$translate")

const OT_REQUEST_FIELDS = ["name", "ot_date", "claimed_hours", "compensation", "docstatus"]
const FILTER_CONFIG = [
	{ fieldname: "ot_date", fieldtype: "Date", label: __("OT Date") },
	{
		fieldname: "compensation",
		fieldtype: "Select",
		label: __("Compensation"),
		options: "\nOvertime Pay\nReplacement Leave",
	},
]
</script>
