<!--
  The year's public holidays, one list (audit-pages PAGE-20): opened as a
  sheet from More's "Public holidays" row. The days still to come: the list
  is for planning (PAGE-20), and a past holiday plans nothing.
-->
<template>
	<div class="flex flex-col gap-3 px-4 pt-6 pb-8">
		<h2 class="text-card-title text-ink">{{ __("Public holidays") }}</h2>
		<GListPanel v-if="holidays.loading && !holidays.data" loading />
		<ResourceError v-else-if="holidays.error" :resource="holidays" what="your holiday calendar" />
		<GListPanel v-else-if="upcoming.length">
			<GListRow
				v-for="holiday in upcoming"
				:key="holiday.holiday_date"
				:label="__(holiday.description)"
				:amount="$dayjs(holiday.holiday_date).format('ddd D MMM')"
				:tappable="false"
			/>
		</GListPanel>
		<p v-else class="text-caption text-ink-600">
			{{ __("No public holidays ahead are listed yet.") }}
		</p>
	</div>
</template>

<script setup>
import { computed, inject } from "vue"
import { createResource } from "frappe-ui"

import GListPanel from "@/components/glass/GListPanel.vue"
import GListRow from "@/components/glass/GListRow.vue"
import ResourceError from "@/components/ResourceError.vue"

const employee = inject("$employee")
const $dayjs = inject("$dayjs")
const __ = inject("$translate")

const holidays = createResource({
	url: "hrms.api.get_holidays_for_employee",
	params: { employee: employee.data?.name },
	auto: true,
})

const upcoming = computed(() =>
	(holidays.data || []).filter(
		(holiday) => !$dayjs(holiday.holiday_date).isBefore($dayjs(), "day")
	)
)
</script>
