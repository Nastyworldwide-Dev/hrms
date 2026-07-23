<template>
	<div class="flex flex-col w-full">
		<div class="flex flex-row items-baseline justify-between mb-2.5">
			<span class="m-kicker">{{ __("Upcoming Holidays") }}</span>
			<span
				v-if="holidays?.data?.length"
				id="open-holiday-list"
				class="text-[11px] text-accent underline underline-offset-[3px] cursor-pointer"
			>
				{{ __("View All") }}
			</span>
		</div>

		<div class="border-t-2 border-divider" v-if="upcomingHolidays?.length">
			<div
				class="flex flex-row items-center justify-between py-3 border-b border-divider"
				v-for="holiday in upcomingHolidays"
				:key="holiday.holiday_date"
			>
				<span class="text-[15px] text-inkbase">
					{{ __(holiday.description) }}
				</span>
				<span class="font-sans font-extrabold text-[12px] uppercase text-inkbase whitespace-nowrap">
					{{ compactHolidayDate(holiday) }}
				</span>
			</div>
		</div>

		<EmptyState :message="__('You have no upcoming holidays')" v-else />
	</div>

	<ion-modal
		ref="modal"
		v-if="holidays?.data?.length"
		trigger="open-holiday-list"
		:initial-breakpoint="1"
		:breakpoints="[0, 1]"
	>
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
						<div class="text-[15px] font-normal text-inkbase">
							{{ __(holiday.description) }}
						</div>
					</div>
					<div
						:class="[
							'text-base font-bold',
							holiday.is_upcoming ? 'text-inkbase' : 'text-ink-500',
						]"
					>
						{{ holiday.formatted_holiday_date }}
					</div>
				</div>
			</div>
		</div>
	</ion-modal>
</template>

<script setup>
import { inject, computed } from "vue"
import { IonModal } from "@ionic/vue"
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
	const filteredHolidays = holidays.data?.filter(
		(holiday) => holiday.is_upcoming
	)

	// show only 5 upcoming holidays
	return filteredHolidays?.slice(0, 5)
})
</script>
