<template>
	<ListItem>
		<template #left>
			<div class="flex flex-col items-start gap-1">
				<div class="text-button-label font-semibold text-inkbase">
					{{ formattedTime }}
				</div>
				<!-- data-visual-mask: "Yesterday" becomes "20 Aug" once the row ages
				     past the relative window — a text change with no code change. -->
				<div class="text-xs text-ink-600" data-visual-mask>{{ dayLabel }}</div>
			</div>
		</template>
		<template #right>
			<GBadge :variant="props.doc.log_type === 'IN' ? 'accent' : 'open'">
				{{ __(tapWord(props.doc.log_type)) }}
			</GBadge>
		</template>
	</ListItem>
</template>

<script setup>
import { siteTime } from "@/utils/siteTime"
import { tapWord } from "@/utils/daySheet"
import GBadge from "@/components/glass/GBadge.vue"
import { computed, inject } from "vue"

import ListItem from "@/components/ListItem.vue"

const dayjs = inject("$dayjs")
const __ = inject("$translate")

const props = defineProps({
	doc: {
		type: Object,
	},
})

const formattedTime = computed(() => siteTime(props.doc.time).format("h:mm a"))

const dayLabel = computed(() => {
	const date = siteTime(props.doc.time)

	if (date.isToday()) return __("Today")
	if (date.isYesterday()) return __("Yesterday")
	if (date.isSame(dayjs(), "year")) return date.format("D MMM")
	return date.format("D MMM, YYYY")
})
</script>
