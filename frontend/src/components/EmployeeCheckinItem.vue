<template>
	<ListItem>
		<template #left>
			<div class="flex flex-col items-start gap-1">
				<div class="text-[15px] font-semibold text-inkbase">
					{{ formattedTime }}
				</div>
				<div class="text-xs text-ink-600">{{ dayLabel }}</div>
			</div>
		</template>
		<template #right>
			<span
				class="m-chip"
				:class="props.doc.log_type === 'IN' ? 'm-chip-outline' : 'm-chip-solid'"
			>
				{{ __(props.doc.log_type, null, "Employee Checkin") }}
			</span>
		</template>
	</ListItem>
</template>

<script setup>
import { computed, inject } from "vue"

import ListItem from "@/components/ListItem.vue"

const dayjs = inject("$dayjs")
const __ = inject("$translate")

const props = defineProps({
	doc: {
		type: Object,
	},
})

const formattedTime = computed(() => dayjs(props.doc.time).format("hh:mm a"))

const dayLabel = computed(() => {
	const date = dayjs(props.doc.time)

	if (date.isToday()) return __("Today")
	if (date.isYesterday()) return __("Yesterday")
	if (date.isSame(dayjs(), "year")) return date.format("D MMM")
	return date.format("D MMM, YYYY")
})
</script>
