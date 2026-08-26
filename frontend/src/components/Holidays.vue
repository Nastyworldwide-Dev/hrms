<template>
	<div class="flex flex-col w-full">
		<div class="flex flex-row items-baseline justify-between mb-2.5">
			<span class="g-eyebrow">{{ __("Upcoming Holidays") }}</span>
			<span
				v-if="holidays?.data?.length"
				id="open-holiday-list"
				class="g-seclink text-kra-label text-accent-ink underline underline-offset-link cursor-pointer"
			>
				{{ __("View All") }}
			</span>
		</div>

		<!-- §15.1: one panel for the list, not one surface per holiday -->
		<GListPanel v-if="upcomingHolidays?.length">
			<GListRow
				v-for="holiday in upcomingHolidays"
				:key="holiday.holiday_date"
				:label="__(holiday.description)"
				:amount="compactHolidayDate(holiday)"
				:tappable="false"
			/>
		</GListPanel>

		<ResourceError v-else-if="holidays.error" :resource="holidays" what="your holiday calendar" />
		<GEmptyState
			v-else
			:title="__('No upcoming holidays')"
			:body="__('Your holiday calendar will fill in as the year is published')"
		/>
	</div>

	<GModal v-if="holidays?.data?.length" trigger="open-holiday-list">
		<div class="bg-ground w-full flex flex-col items-center justify-center pb-5">
			<div class="w-full pt-8 pb-5 border-b-2 border-divider text-center">
				<span class="text-inkbase font-extrabold text-lg">{{ __("Holiday List") }}</span>
			</div>
			<div class="w-full flex flex-col items-center justify-center gap-5 p-4">
				<div
					v-for="holiday in holidays.data"
					:key="holiday.holiday_date"
					class="flex flex-row items-center justify-between w-full"
				>
					<div class="flex flex-row items-center gap-3 grow">
						<FeatherIcon name="calendar" class="h-5 w-5 text-ink-500" />
						<div class="text-button-label font-normal text-inkbase">
							{{ __(holiday.description) }}
						</div>
					</div>
					<div
						:class="['text-base font-bold', holiday.is_upcoming ? 'text-inkbase' : 'text-ink-500']"
					>
						{{ holiday.formatted_holiday_date }}
					</div>
				</div>
			</div>
		</div>
	</GModal>
</template>

<script setup>
import GModal from "@/components/glass/GModal.vue"
import GEmptyState from "@/components/glass/GEmptyState.vue"
import GListRow from "@/components/glass/GListRow.vue"
import GListPanel from "@/components/glass/GListPanel.vue"
import { inject, computed } from "vue"
import { FeatherIcon, createResource } from "frappe-ui"

const employee = inject("$employee")
const dayjs = inject("$dayjs")
const __ = inject("$translate")

const holidays = createResource({
	url: "hrms.api.get_holidays_for_employee",
	params: {
		employee: employee.data.name,
	},
	auto: true,
	transform: (data) => {
		return data.map((holiday) => {
			const holidayDate = dayjs(holiday.holiday_date)
			holiday.is_upcoming = holidayDate.isAfter(dayjs())
			holiday.formatted_holiday_date = holidayDate.format("ddd, D MMM YYYY")
			return holiday
		})
	},
})

// Compact uppercase date for the ruled list rows (e.g. "FRI 14 AUG").
const compactHolidayDate = (holiday) =>
	dayjs(holiday.holiday_date).format("ddd D MMM").toUpperCase()

const upcomingHolidays = computed(() => {
	const filteredHolidays = holidays.data?.filter((holiday) => holiday.is_upcoming)

	// show only 5 upcoming holidays
	return filteredHolidays?.slice(0, 5)
})
</script>
