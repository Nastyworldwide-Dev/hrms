<template>
	<div class="flex flex-col w-full">
		<div class="flex flex-row items-baseline justify-between mb-3">
			<span class="m-kicker">{{ __("Leave Balance") }}</span>
			<router-link
				:to="{ name: 'LeaveApplicationListView' }"
				v-slot="{ navigate }"
				v-if="leaveBalance.data"
			>
				<span
					@click="navigate"
					class="text-[11px] text-accent underline underline-offset-[3px] cursor-pointer"
				>
					{{ __("View Leave History") }}
				</span>
			</router-link>
		</div>

		<!-- Leave Balance stat cells -->
		<div
			class="grid grid-cols-3 border-t-2 border-divider"
			v-if="leaveBalance.data"
		>
			<div
				v-for="(allocation, leave_type, index) in leaveBalance.data"
				:key="leave_type"
				class="flex flex-col gap-1.5 px-3 py-3.5"
				:class="index % 3 !== 0 ? 'border-l border-divider' : ''"
			>
				<div class="font-sans font-extrabold text-[26px] leading-none text-inkbase">
					{{ formatLeaveDays(allocation.balance_leaves)
					}}<span class="text-[13px] font-normal text-ink-500">
						/{{ formatLeaveDays(allocation.annual_entitlement) }}</span
					>
				</div>
				<div class="m-bar relative" style="height: 4px">
					<div
						class="m-bar-fill"
						:style="{ width: `${allocation.balance_percentage}%` }"
					></div>
					<div
						v-if="allocation.prorated"
						class="m-bar-band"
						:style="{ width: `${allocation.prorated_percentage}%` }"
					></div>
				</div>
				<div class="text-[9px] tracking-[0.08em] uppercase text-ink-600 leading-tight">
					{{ __(leave_type, null, "Leave Type") }}
				</div>
				<div
					v-if="allocation.prorated"
					class="text-[9px] text-ink-600 leading-tight"
				>
					{{
						__("Pro-rated: {0} allocated for {1}", [
							formatLeaveDays(allocation.allocated_leaves),
							allocation.period_year,
						])
					}}
				</div>
				<div
					v-if="allocation.carry_forwarded_leaves > 0"
					class="text-[9px] text-ink-600 leading-tight"
				>
					{{ __("incl. carry-forward") }}
				</div>
			</div>
		</div>

		<EmptyState :message="__('You have no leaves allocated')" v-else />
	</div>
</template>

<script setup>
import { leaveBalance } from "@/data/leaves"
import { formatLeaveDays } from "@/utils/formatters"
import { inject } from "vue"

const __ = inject("$translate")
</script>
