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
					class="text-[11px] text-accent underline underline-offset-link cursor-pointer"
				>
					{{ __("View Leave History") }}
				</span>
			</router-link>
		</div>

		<!-- Leave Balance stat cells -->
		<div
			class="grid grid-cols-3 border-t-2 border-divider"
			v-if="hasBalances"
		>
			<div
				v-for="(allocation, leave_type, index) in leaveBalance.data"
				:key="leave_type"
				class="flex flex-col gap-1.5 px-3 py-3.5"
				:class="index % 3 !== 0 ? 'border-l border-divider' : ''"
			>
				<div class="font-sans font-extrabold text-[26px] leading-none text-inkbase">
					{{ formatLeaveDays(allocation.balance_leaves) }}
				</div>
				<div class="m-bar" style="height: 4px">
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

		<!-- Order matters, and this is the exact confusion HR reported. `hasBalances`
		     is false when the request FAILED just as surely as when the employee
		     genuinely has none, so the empty state was asserting "you have no leaves
		     allocated" about a question that had never been answered. Whatever else
		     is wrong, telling someone their entitlement is zero when we could not
		     read it is the worst available answer. -->
		<ResourceError v-else-if="leaveBalance.error" :resource="leaveBalance" what="your leave balance" />
		<EmptyState :message="__('You have no leaves allocated')" v-else />
	</div>
</template>

<script setup>
import { leaveBalance } from "@/data/leaves"
import { formatLeaveDays } from "@/utils/formatters"
import { computed, inject } from "vue"

const __ = inject("$translate")

// an empty map {} is truthy — without this check the section renders as a
// bare rule instead of the "no leaves allocated" empty state
const hasBalances = computed(
	() => leaveBalance.data && Object.keys(leaveBalance.data).length > 0
)
</script>
