<template>
	<ListItem>
		<template #left>
			<div class="text-[15px] font-semibold text-inkbase">
				{{ title }}
			</div>
		</template>
		<template #right>
			<span class="w-24 text-right text-[13px] text-ink-600 tabular-nums">
				{{ doc?.gross_pay ? formatCurrency(doc.gross_pay, doc.currency) : "" }}
			</span>
			<span class="w-28 text-right text-[15px] font-bold tabular-nums text-inkbase">
				{{ doc?.net_pay ? formatCurrency(doc.net_pay, doc.currency) : "" }}
			</span>
		</template>
	</ListItem>
</template>

<script setup>
import { computed, inject } from "vue"

import ListItem from "@/components/ListItem.vue"

import { formatCurrency } from "@/utils/formatters"

const dayjs = inject("$dayjs")

const props = defineProps({
	doc: {
		type: Object,
	},
})

const title = computed(() => {
	if (dayjs(props.doc.start_date).isSame(props.doc.end_date, "month")) {
		// monthly salary
		return dayjs(props.doc.start_date).format("MMM YYYY")
	} else {
		// quarterly, bimonthly, etc
		return `${dayjs(props.doc.start_date).format("MMM YYYY")} - ${dayjs(
			props.doc.end_date
		).format("MMM YYYY")}`
	}
})
</script>
