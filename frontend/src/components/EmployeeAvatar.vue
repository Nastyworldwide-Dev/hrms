<!--
  EmployeeAvatar — resolves an employee/user id to a person, then renders
  GAvatar. It is a DATA wrapper, not an avatar treatment: every visual decision
  belongs to GAvatar (§10.3).

  It used to wrap frappe-ui's `Avatar` inside a `grayscale` span, which made it
  the third of four avatar forms in the app — on frappe-ui's own size scale
  (`sm` = 20px, `lg` = 28px, radius 5–6px) rather than the Glass tokens, and
  desaturated, which was a Modernist device. Both are gone.

  The `size` prop keeps its string API because three call sites pass strings;
  the strings now resolve to the px GAvatar takes.
-->
<template>
	<div v-if="showLabel" class="flex flex-row items-center gap-2">
		<GAvatar
			v-if="employee"
			:label="employee?.employee_name"
			:image="employee?.image"
			:size="px"
		/>
		<div class="text-base text-ink-800 grow">
			{{ employee?.employee_name }}
		</div>
	</div>

	<GAvatar
		v-else
		:label="employee?.employee_name"
		:image="employee?.image"
		:size="px"
	/>
</template>

<script setup>
import { computed } from "vue"
import GAvatar from "@/components/glass/GAvatar.vue"
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

// frappe-ui's scale, preserved in px so nothing jumps: sm was w-5 (20px) and
// lg was w-7 (28px). Both sit under §14.1's 44px, which is fine — an avatar is
// not a touch target here; the row around it is.
const SIZES = { xs: 16, sm: 20, md: 24, lg: 28, xl: 32, "2xl": 40, "3xl": 46 }
const px = computed(() => SIZES[props.size] ?? SIZES.sm)

const employee = computed(() => {
	if (props.employeeID) {
		return getEmployeeInfo(props.employeeID)
	} else if (props.userID) {
		return getEmployeeInfoByUserID(props.userID)
	}
	return null
})
</script>
