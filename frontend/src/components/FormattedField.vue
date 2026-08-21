<template>
	<div v-if="!props.value" class="text-ink-600 text-base">-</div>

	<Badge
		v-else-if="props.fieldtype === 'Select'"
		variant="outline"
		:theme="colorMap[props.value]"
		:label="__(props.value)"
		size="md"
	/>

	<div v-else-if="props.fieldtype === 'Date'" class="text-inkbase text-base">
		{{ dayjs(props.value).format("D MMM YYYY") }}
	</div>

	<Input
		v-else-if="props.fieldtype === 'Check'"
		type="checkbox"
		label=""
		v-model="props.value"
		:disabled="true"
		class="text-accent"
	/>

	<div
		v-else-if="['Small Text', 'Text', 'Long Text'].includes(props.fieldtype)"
		class="text-inkbase text-sm bg-surface border border-divider py-3 px-3 mt-2"
	>
		{{ props.value }}
	</div>

	<EmployeeAvatar
		v-else-if="props.fieldtype === 'Link' && ['employee', 'reports_to'].includes(props.fieldname)"
		:employeeID="props.value"
		:showLabel="true"
	/>

	<div
		v-else-if="props.fieldtype === 'geolocation'"
		class="border border-divider rounded-panel translate-z-0 block overflow-hidden w-full h-170 mt-2"
	>
		<iframe
			width="100%"
			height="170"
			frameborder="0"
			scrolling="no"
			marginheight="0"
			marginwidth="0"
			style="border: 0"
			:src="`https://maps.google.com/maps?q=${getCoordinates(props.value).latitude},${
				getCoordinates(props.value).longitude
			}&hl=en&z=15&amp;output=embed`"
		>
		</iframe>
	</div>

	<div v-else class="text-inkbase text-base">{{ props.value }}</div>
</template>

<script setup>
import { inject } from "vue"
import { Badge, FormControl, Input } from "frappe-ui"

import EmployeeAvatar from "@/components/EmployeeAvatar.vue"

const dayjs = inject("$dayjs")

const props = defineProps({
	value: [String, Number, Boolean, Array, Object],
	fieldtype: String,
	fieldname: String,
})

const colorMap = {
	Approved: "green",
	Rejected: "red",
	Open: "orange",
}

const getCoordinates = (value) => {
	const [longitude, latitude] = JSON.parse(value).features[0].geometry.coordinates
	return { longitude, latitude }
}
</script>
