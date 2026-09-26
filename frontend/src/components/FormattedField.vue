<template>
	<div v-if="!props.value" class="text-ink-600 text-row-label">-</div>

	<!-- One status map (utils/requestStatus.js via GStatusChip): the local
	     three-entry colour table this used to carry disagreed with every list. -->
	<GStatusChip
		v-else-if="props.fieldtype === 'Select'"
		:status="props.value"
		:label="__(props.value)"
	/>

	<div v-else-if="props.fieldtype === 'Date'" class="text-inkbase text-row-label">
		{{ dayjs(props.value).format("D MMM YYYY") }}
	</div>

	<!-- Read-only display: :model-value, not v-model — this component only ever
	     shows a formatted value, and v-model here silently mutated the "value"
	     prop (harmless while :disabled locks the box, but wrong data flow and
	     a real Vue warning either way). -->
	<GCheckbox
		v-else-if="props.fieldtype === 'Check'"
		:model-value="props.value"
		:disabled="true"
	/>

	<div
		v-else-if="['Small Text', 'Text', 'Long Text'].includes(props.fieldtype)"
		class="text-inkbase text-row-label bg-surface border border-divider py-3 px-3 mt-2"
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

	<div v-else class="text-inkbase text-row-label">{{ props.value }}</div>
</template>

<script setup>
import { inject } from "vue"
import GCheckbox from "@/components/glass/GCheckbox.vue"
import GStatusChip from "@/components/glass/GStatusChip.vue"

import EmployeeAvatar from "@/components/EmployeeAvatar.vue"

const dayjs = inject("$dayjs")

const props = defineProps({
	value: [String, Number, Boolean, Array, Object],
	fieldtype: String,
	fieldname: String,
})

const getCoordinates = (value) => {
	const [longitude, latitude] = JSON.parse(value).features[0].geometry.coordinates
	return { longitude, latitude }
}
</script>
