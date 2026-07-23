<template>
	<BaseLayout :pageTitle="__('Salary Slips')">
		<template #body>
			<div
				class="flex flex-col w-full max-w-2xl mx-auto px-4 py-7 gap-8 lg:max-w-none lg:mx-0 lg:grid lg:grid-cols-[320px_1fr] lg:gap-x-0 lg:p-7 lg:items-start"
			>
				<div class="contents lg:flex lg:flex-col lg:gap-8 lg:pr-8">
				<!-- Year to date -->
				<div
					v-if="lastSalarySlip && lastSalarySlip.year_to_date"
					class="border-t-2 border-divider pt-3.5"
				>
					<div
						class="text-[10px] tracking-[0.1em] uppercase text-ink-600 font-sans font-extrabold"
					>
						{{ __("Year To Date") }}
					</div>
					<div class="font-sans font-extrabold text-[34px] leading-[1.05] mt-1.5 tabular-nums">
						{{
							formatCurrency(
								lastSalarySlip.year_to_date,
								lastSalarySlip.currency
							)
						}}
					</div>
				</div>

				<!-- Payroll period selector -->
				<div>
					<label class="block text-xs mb-1.5 text-ink-700">
						{{ __("Payroll Period") }}
					</label>
					<Autocomplete
						class="w-full"
						:placeholder="__('Select Payroll Period')"
						v-model="selectedPeriod"
						:options="payrollPeriods.data"
					/>
				</div>
				</div>

				<!-- Slip table -->
				<div class="lg:border-l lg:border-divider lg:pl-8">
					<div
						v-if="documents.data?.length"
						class="flex flex-col overflow-auto w-full"
					>
						<div
							class="flex flex-row items-center justify-between border-b-2 border-divider pb-2"
						>
							<span class="text-[10px] tracking-[0.08em] uppercase text-ink-600">
								{{ __("Period") }}
							</span>
							<div class="flex flex-row gap-2">
								<span
									class="w-24 text-[10px] tracking-[0.08em] uppercase text-ink-600 text-right"
								>
									{{ __("Gross") }}
								</span>
								<span
									class="w-28 text-[10px] tracking-[0.08em] uppercase text-ink-600 text-right"
								>
									{{ __("Net Pay") }}
								</span>
							</div>
						</div>
						<div
							class="m-row cursor-pointer"
							v-for="link in documents.data"
							:key="link.name"
						>
							<router-link
								:to="{
									name: 'SalarySlipDetailView',
									params: { id: link.name },
								}"
								v-slot="{ navigate }"
							>
								<SalarySlipItem :doc="link" @click="navigate" />
							</router-link>
						</div>
						<div class="text-[11px] text-ink-500 mt-2.5">
							{{ __("Tap a row to view the full slip · PDF download available per slip") }}
						</div>
					</div>
					<EmptyState :message="__('No salary slips found')" v-else />
				</div>
			</div>
		</template>
	</BaseLayout>
</template>

<script setup>
import { inject, ref, computed, watch, onMounted, onBeforeUnmount } from "vue"
import { Autocomplete, createListResource } from "frappe-ui"

import BaseLayout from "@/components/BaseLayout.vue"
import EmptyState from "@/components/EmptyState.vue"
import SalarySlipItem from "@/components/SalarySlipItem.vue"

import { formatCurrency } from "@/utils/formatters"

let selectedPeriod = ref({})
let periodsByName = ref({})

const employee = inject("$employee")
const dayjs = inject("$dayjs")
const socket = inject("$socket")
const __ = inject("$translate")

const payrollPeriods = createListResource({
	doctype: "Payroll Period",
	fields: ["name", "start_date", "end_date"],
	filters: {
		company: employee.data?.company,
	},
	orderBy: "start_date desc",
	auto: true,
	transform(data) {
		return data.map((period) => {
			periodsByName.value[period.name] = period
			return {
				label: getPeriodLabel(period),
				value: period.name,
			}
		})
	},
	onSuccess: (data) => {
		selectedPeriod.value = data[0]
	},
})

const documents = createListResource({
	doctype: "Salary Slip",
	fields: [
		"name",
		"start_date",
		"end_date",
		"currency",
		"gross_pay",
		"net_pay",
		"year_to_date",
	],
	filters: {
		employee: employee.data?.name,
		docstatus: 1,
	},
	orderBy: "end_date desc",
})

const lastSalarySlip = computed(() => documents.data?.[0])

function getPeriodLabel(period) {
	return `${dayjs(period?.start_date).format("MMM YYYY")} - ${dayjs(
		period?.end_date
	).format("MMM YYYY")}`
}

watch(
	() => selectedPeriod.value,
	(value) => {
		let period = periodsByName.value[value?.value]
		documents.filters.start_date = [
			"between",
			[period?.start_date, period?.end_date],
		]
		documents.reload()
	}
)

onMounted(() => {
	socket.on("hrms:update_salary_slips", (data) => {
		if (data.employee === employee.data.name) {
			documents.reload()
		}
	})
})

onBeforeUnmount(() => {
	socket.off("hrms:update_salary_slips")
})
</script>
