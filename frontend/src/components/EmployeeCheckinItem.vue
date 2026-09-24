<template>
	<!-- One check-in, as iOS draws a row (alpha.7 0.8): "In" or "Out" leading,
	     the time trailing in grey. The day is the group heading above
	     (ListView), not repeated on each row; no chips, no bold time. -->
	<button type="button" class="g-form-row g-checkin-row" @click="$emit('click', $event)">
		<span class="g-form-row__label">{{ __(tapWord(props.doc.log_type)) }}</span>
		<span class="g-checkin-row__time">{{ formattedTime }}</span>
		<ChevronRight class="g-checkin-row__chevron" aria-hidden="true" />
	</button>
</template>

<script setup>
import { siteTime } from "@/utils/siteTime"
import { tapWord } from "@/utils/daySheet"
import { computed, inject } from "vue"
import { ChevronRight } from "lucide-vue-next"

const __ = inject("$translate")

const props = defineProps({
	doc: {
		type: Object,
	},
})
defineEmits(["click"])

const formattedTime = computed(() => siteTime(props.doc.time).format("h:mm a"))
</script>
