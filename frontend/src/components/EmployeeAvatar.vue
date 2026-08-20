<template>
	<div v-if="showLabel" class="flex flex-row items-center gap-2">
		<span class="grayscale inline-flex">
			<Avatar
				v-if="employee"
				:label="employee?.employee_name"
				:image="employee?.image"
				:size="props.size"
			/>
		</span>
		<div class="text-base text-ink-800 grow">
			{{ employee?.employee_name }}
		</div>
	</div>

	<span v-else class="grayscale inline-flex">
		<Avatar
			:label="employee?.employee_name"
			:image="employee?.image"
			:size="props.size"
		/>
	</span>
</template>

<script setup>
import { computed } from "vue"
import { Avatar } from "frappe-ui"
import { getEmployeeInfo, getEmployeeInfoByUserID } from "@/data/employees"

const props = defineProps({
	employeeID: {
		type: String,
		required: false,
	},
	userID: {
		type: String,
		required: false,
	},
	size: {
		type: String,
		default: "sm",
	},
	showLabel: {
		type: Boolean,
		default: false,
	},
})

const employee = computed(() => {
	if (props.employeeID) {
		return getEmployeeInfo(props.employeeID)
	} else if (props.userID) {
		return getEmployeeInfoByUserID(props.userID)
	}
})
</script>
