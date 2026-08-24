<template>
	<!-- Table -->
	<div
		v-if="doc?.expenses"
		class="flex flex-col mt-5 border-t-2 border-divider overflow-auto"
	>
		<div
			class="flex flex-row py-3.5 px-0.5 items-center justify-between cursor-pointer border-b border-divider"
			v-for="(item, idx) in doc?.expenses"
			:key="idx"
		>
			<div class="flex flex-col w-full justify-center gap-2.5">
				<div class="flex flex-row items-center justify-between">
					<div class="flex flex-row items-start gap-3 grow">
						<div class="flex flex-col items-start gap-1.5">
							<div class="text-button-label font-semibold text-inkbase">
								{{ __(item.expense_type) }}
							</div>
							<div class="text-xs font-normal text-ink-600">
								<span>
									{{
										__("{0}: {1}", [
											__("Sanctioned"),
											formatCurrency(item.sanctioned_amount || 0, doc.currency),
										])
									}}
								</span>
								<span class="whitespace-pre"> &middot; </span>
								<span class="whitespace-nowrap" v-if="item.expense_date">
									{{ dayjs(item.expense_date).format("D MMM") }}
								</span>
							</div>
						</div>
					</div>
					<span class="text-button-label font-bold tabular-nums text-inkbase">
						{{ formatCurrency(item.amount, doc.currency) }}
					</span>
				</div>
			</div>
		</div>
	</div>
</template>

<script setup>
import { inject } from "vue"

import { formatCurrency } from "@/utils/formatters"

defineProps({
	doc: {
		type: Object,
		required: true,
	},
})

const dayjs = inject("$dayjs")
</script>
