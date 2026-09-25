<!--
  The year's public holidays, one list (audit-pages PAGE-20): opened as a
  sheet from More's "Public holidays" row. The days still to come: the list
  is for planning (PAGE-20), and a past holiday plans nothing.
  The sheet owns the title. The days are rows in one inset group, as every
  sheet's (alpha.9 D25), and the next holiday carries a "Next" chip.
-->
<template>
	<div class="flex flex-col px-4 pb-8">
		<GListPanel v-if="holidays.loading && !holidays.data" loading />
		<ResourceError v-else-if="holidays.error" :resource="holidays" what="your holiday calendar" />
		<!-- One inset group like every other sheet (alpha.9 D25): the rows were
		     hand-ruled on the sheet, and "none listed" was a loose grey line. -->
		<GListPanel v-else-if="upcoming.length">
			<GListRow
				v-for="(holiday, index) in upcoming"
				:key="holiday.holiday_date"
				:label="__(holiday.description)"
				:amount="$dayjs(holiday.holiday_date).format('ddd D MMM')"
				:tappable="false"
			>
				<template v-if="index === 0" #badge>
					<GStatusChip status="Next" :label="__('Next')" />
				</template>
			</GListRow>
		</GListPanel>
		<GListPanel v-else>
			<GListRow :label="__('No public holidays ahead are listed yet.')" :tappable="false" />
		</GListPanel>
	</div>
</template>

<script setup>
import { computed, inject } from "vue"
import { createResource } from "frappe-ui"

import GListPanel from "@/components/glass/GListPanel.vue"
import GListRow from "@/components/glass/GListRow.vue"
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
