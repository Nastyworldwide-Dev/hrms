<template>
	<ListItem>
		<template #left>
			<div class="flex flex-col items-start gap-1">
				<div class="text-button-label font-semibold text-inkbase">
					{{ props.doc.shift_type }}
				</div>
				<div class="text-xs text-ink-600">
					<span>{{ props.doc.shift_dates || getShiftDates(props.doc) }}</span>
					<span v-if="props.doc.end_date" class="whitespace-pre"> &middot; </span>
					<span v-if="props.doc.end_date" class="whitespace-nowrap">{{
						daysWords(props.doc.total_shift_days || getTotalShiftDays(props.doc))
					}}</span>
				</div>
				<div v-if="props.doc.shift_location" class="text-xs text-ink-600 whitespace-nowrap">
					&#128205; {{ props.doc.shift_location }}
				</div>
			</div>
		</template>
		<template #right>
			<span v-if="props.doc.shift_timing" class="text-xs font-bold tabular-nums text-inkbase">
				{{ props.doc.shift_timing }}
			</span>
			<GStatusChip v-else :status="status" :label="label" />
		</template>
	</ListItem>
</template>

<script setup>
import { daysWords } from "@/utils/countWords"
import GStatusChip from "@/components/glass/GStatusChip.vue"
import { computed, inject } from "vue"

import ListItem from "@/components/ListItem.vue"
import { getShiftDates, getTotalShiftDays } from "@/data/attendance"

const __ = inject("$translate")

const props = defineProps({
	doc: {
		type: Object,
	},
})

// The COLOUR's input: a real workflow state where one exists, and otherwise
// Frappe's own vocabulary, which GStatusChip already knows how to colour.
const status = computed(() => {
	if (props.workflowStateField) return props.doc[props.workflowStateField]
	return props.doc.docstatus ? "Submitted" : "Draft"
})

// The WORD an employee reads. Separate from `status` on purpose: the chip
// colours from the state and reads from the label, and this component had
// been handing it the same string for both — untranslated, and invented from
// `docstatus` besides.
//
// "Draft" and "Submitted" are Frappe's two words for "this row is saved" and
// "this row is not". Neither describes a shift. "Draft" is the worse of the
// two: it reads as "you have not finished it" when the shift is real and
// simply has not been submitted by whoever does the rostering — which is not
// the employee, and not something they can act on.
//
// A real workflow state still passes through translated, because a workflow
// somebody configured says what it means.
const label = computed(() => {
	if (props.workflowStateField) return __(status.value, null, "Shift Assignment")
	return props.doc.docstatus ? __("Scheduled") : __("Not scheduled yet")
})
</script>
