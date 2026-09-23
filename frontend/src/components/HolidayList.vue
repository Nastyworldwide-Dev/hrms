<!--
  The year's public holidays, one list (audit-pages PAGE-20): opened as a
  sheet from More's "Public holidays" row. The days still to come: the list
  is for planning (PAGE-20), and a past holiday plans nothing.
  The sheet owns the title. The list is flat (plain divided rows, no card
  inside the sheet), and the first row, the next holiday, carries a "Next" chip.
-->
<template>
	<div class="flex flex-col px-4 pb-8">
		<GListPanel v-if="holidays.loading && !holidays.data" loading />
		<ResourceError v-else-if="holidays.error" :resource="holidays" what="your holiday calendar" />
		<ul v-else-if="upcoming.length" class="flex flex-col">
			<li
				v-for="(holiday, index) in upcoming"
				:key="holiday.holiday_date"
				class="flex flex-row items-center justify-between gap-3 py-3 border-b border-divider last:border-b-0"
			>
				<span class="flex flex-row items-center gap-2 min-w-0">
					<span class="text-sm text-ink">{{ __(holiday.description) }}</span>
					<GStatusChip v-if="index === 0" status="Next" :label="__('Next')" />
				</span>
				<span class="text-sm text-ink-600 tabular-nums shrink-0">
					{{ $dayjs(holiday.holiday_date).format("ddd D MMM") }}
				</span>
			</li>
		</ul>
		<p v-else class="text-caption text-ink-600">
			{{ __("No public holidays ahead are listed yet.") }}
		</p>
	</div>
</template>

<script setup>
import { computed, inject } from "vue"
import { createResource } from "frappe-ui"

import GListPanel from "@/components/glass/GListPanel.vue"
import GStatusChip from "@/components/glass/GStatusChip.vue"
import ResourceError from "@/components/ResourceError.vue"

const employee = inject("$employee")
const $dayjs = inject("$dayjs")
const __ = inject("$translate")

const holidays = createResource({
	url: "hrms.api.get_holidays_for_employee",
	params: { employee: employee.data?.name },
	auto: true,
})

//: Soonest first, so the first row is the next holiday.
const upcoming = computed(() =>
	(holidays.data || [])
		.filter((holiday) => !$dayjs(holiday.holiday_date).isBefore($dayjs(), "day"))
		.sort((a, b) => $dayjs(a.holiday_date).valueOf() - $dayjs(b.holiday_date).valueOf())
)
</script>
