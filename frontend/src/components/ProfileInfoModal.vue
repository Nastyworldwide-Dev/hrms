<!-- The rows of the employee's details; the sheet around it (Profile.vue) owns
     the title, so this draws no heading of its own. -->
<template>
	<div class="w-full flex flex-col pb-6">
		<div class="w-full flex flex-col px-4">
			<div
				v-for="item in data"
				:key="item.fieldname"
				class="flex flex-row items-center justify-between w-full gap-4 py-3.5 border-b border-divider last:border-b-0"
			>
				<div class="text-ink-600 text-xs shrink-0">{{ item.label }}</div>
				<FormattedField
					class="text-sm text-inkbase text-right"
					:value="item.value"
					:fieldtype="item.fieldtype"
					:fieldname="item.fieldname"
				/>
			</div>
		</div>
	</div>
</template>

<script setup>
import FormattedField from "@/components/FormattedField.vue"

defineProps({
	data: {
		type: Array,
		required: true,
	},
})
</script>
