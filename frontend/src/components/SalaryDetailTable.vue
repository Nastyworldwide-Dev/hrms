<template>
	<!-- Header -->
	<div
		class="flex flex-row justify-between items-baseline border-b-2 border-divider pb-2"
	>
		<span class="text-[10px] tracking-[0.08em] uppercase text-ink-600">
			{{ type }}
		</span>
		<span class="font-sans font-extrabold text-sm tabular-nums">
			{{ total }}
		</span>
	</div>

	<!-- Table -->
	<div v-if="items" class="flex flex-col overflow-auto">
		<div
			class="m-row flex flex-row py-3.5 items-center justify-between gap-3"
			v-for="(item, idx) in items"
			:key="idx"
		>
			<div
				class="font-sans font-semibold text-[15px] whitespace-nowrap overflow-hidden text-ellipsis"
			>
				{{ item.salary_component }}
			</div>
			<span class="font-sans font-extrabold text-[15px] tabular-nums">
				{{ formatCurrency(item.amount, salarySlip.currency) }}
			</span>
		</div>
	</div>
	<EmptyState
		v-else
		:message="__('No {0} added', [props.type?.toLowerCase()])"
		:isTableField="true"
	/>
</template>

<script setup>
import { computed,inject } from "vue"

import EmptyState from "@/components/EmptyState.vue"
import { formatCurrency } from "@/utils/formatters"

const __ = inject("$translate")

const props = defineProps({
	salarySlip: {
		type: Object,
		required: true,
	},
	type: {
		type: String,
		required: true,
	},
	isReadOnly: {
		type: Boolean,
		default: false,
	},
})

const items = computed(() => {
	return props.type === "Earnings"
		? props.salarySlip.earnings
		: props.salarySlip.deductions
})

const total = computed(() => {
	return props.type === "Earnings"
		? props.salarySlip.gross_pay
		: props.salarySlip.total_deduction
})
</script>
