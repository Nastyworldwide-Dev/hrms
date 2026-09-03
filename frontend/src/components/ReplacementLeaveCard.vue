<template>
	<div class="flex flex-col w-full">
		<div class="flex flex-row items-baseline justify-between mb-3">
			<span class="g-eyebrow">{{ __("Replacement Leave") }}</span>
			<router-link :to="{ name: 'ReplacementLeaveView' }" v-slot="{ navigate }">
				<span
					@click="navigate"
					class="g-seclink text-kra-label text-accent-ink underline underline-offset-link cursor-pointer"
				>
					{{ __("View Claims") }}
				</span>
			</router-link>
		</div>
		<ResourceError :resource="bank" what="your replacement leave bank" />

		<div class="flex flex-row items-center justify-between border-t-2 border-divider px-3 py-3.5">
			<div class="flex flex-col gap-1.5">
				<div class="font-sans font-extrabold text-ring-centre leading-none text-inkbase">
					{{ formatLeaveDays(bank.data?.balance_days ?? 0) }}
				</div>
				<div class="g-eyebrow">
					{{ __("days available") }}
				</div>
				<div class="text-kra-label text-ink-600 leading-tight">
					{{
						__("{0} bank: {1} h unclaimed · 0.5 day = {2} h", [
							monthLabel,
							bank.data?.hours_available ?? 0,
							halfDayHours,
						])
					}}
				</div>
			</div>
			<router-link :to="{ name: 'ReplacementLeaveClaimFormView' }" v-slot="{ navigate }">
				<!-- Secondary, not primary (§18: one primary action per screen).
				     This was a second chartreuse fill on a screen whose primary is
				     "Request a Leave", square-cornered, and 37px tall. -->
				<button
					@click="navigate"
					class="g-touch flex items-center justify-center border border-divider rounded-action text-inkbase px-3.5 py-2.5 font-sans font-extrabold text-xs uppercase tracking-wide hover:bg-icon-bg"
				>
					{{ __("Claim") }}
				</button>
			</router-link>
		</div>
	</div>
</template>

<script setup>
import { createResource } from "frappe-ui"
import { computed, inject } from "vue"

import { formatLeaveDays } from "@/utils/formatters"
import { settings } from "@/data/settings"

const employee = inject("$employee")
const __ = inject("$translate")
const dayjs = inject("$dayjs")

// half a leave day in banked-overtime hours, from HR's configurable ratio (default 8/day)
const halfDayHours = computed(() => (settings.data?.replacement_leave_hours_per_day ?? 8) / 2)

const bank = createResource({
	url: "hrms.api.get_replacement_leave_bank_summary",
	params: { employee: employee.data.name },
	auto: true,
})

const monthLabel = computed(() =>
	bank.data?.month_start ? dayjs(bank.data.month_start).format("MMM") : ""
)
</script>
import ResourceError from "@/components/ResourceError.vue"
