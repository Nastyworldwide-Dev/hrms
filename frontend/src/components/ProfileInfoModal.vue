<template>
	<div
		class="bg-ground w-full flex flex-col pb-6 max-h-sheet overflow-y-auto"
	>
		<!-- Header -->
		<div
			class="w-full flex flex-col gap-1 px-4 pt-6 pb-4 sticky top-0 z-overlay bg-ground"
		>
			<span class="g-eyebrow">{{ __("Employee") }}</span>
			<span class="font-sans font-extrabold text-stat-number text-inkbase">
				{{ title }}
			</span>
		</div>

		<div class="w-full flex flex-col px-4 border-t-2 border-divider">
			<div
				v-for="item in data"
				:key="item.fieldname"
				class="flex flex-row items-center justify-between w-full gap-4 py-3.5 border-b border-divider"
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
import { inject } from "vue"
import FormattedField from "@/components/FormattedField.vue"

const __ = inject("$translate")

defineProps({
	title: {
		type: String,
		required: true,
	},
	data: {
		type: Array,
		required: true,
	},
})
</script>
