<template>
	<div class="flex flex-col w-full">
		<div class="flex flex-row items-baseline justify-between mb-3">
			<span class="g-eyebrow">{{ __("Leave Balance") }}</span>
			<router-link
				:to="{ name: 'LeaveApplicationListView' }"
				v-slot="{ navigate }"
				v-if="leaveBalance.data"
			>
				<span
					@click="navigate"
					class="text-kra-label text-accent-ink underline underline-offset-link cursor-pointer"
				>
					{{ __("View Leave History") }}
				</span>
			</router-link>
		</div>

		<!-- §15.2: ONE glass panel with internal --hair dividers, not one card
		     per leave type. The count is dynamic — an employee may have two
		     types or five — and the surface cost is 1 either way. -->
		<GBalanceGrid v-if="hasBalances" :count="balanceCount">
			<GBalanceCard
				v-for="(allocation, leave_type) in leaveBalance.data"
				:key="leave_type"
				:label="__(leave_type, null, 'Leave Type')"
				:remaining="Number(formatLeaveDays(allocation.balance_leaves))"
				:allocated="Number(allocation.allocated_leaves ?? 0)"
				:entitlement="Number(allocation.annual_entitlement ?? 0)"
				:prorated-percentage="allocation.prorated ? allocation.prorated_percentage : 0"
			>
				<template v-if="allocation.prorated || allocation.carry_forwarded_leaves > 0" #note>
					<template v-if="allocation.prorated">
						{{
							__("Pro-rated: {0} allocated for {1}", [
								formatLeaveDays(allocation.allocated_leaves),
								allocation.period_year,
							])
						}}
					</template>
					<template v-if="allocation.carry_forwarded_leaves > 0">
						{{ __("incl. carry-forward") }}
					</template>
				</template>
			</GBalanceCard>
		</GBalanceGrid>

		<!-- Order matters, and this is the exact confusion HR reported. `hasBalances`
		     is false when the request FAILED just as surely as when the employee
		     genuinely has none, so the empty state was asserting "you have no leaves
		     allocated" about a question that had never been answered. Whatever else
		     is wrong, telling someone their entitlement is zero when we could not
		     read it is the worst available answer. -->
		<ResourceError
			v-else-if="leaveBalance.error"
			:resource="leaveBalance"
			what="your leave balance"
		/>
		<GBalanceGrid v-else empty>
			<template #empty>
				<GEmptyState
					:title="__('No leave allocated yet')"
					:body="__('People &amp; Culture are setting this up. Check back shortly.')"
				/>
			</template>
		</GBalanceGrid>
	</div>
</template>

<script setup>
import GEmptyState from "@/components/glass/GEmptyState.vue"
import GBalanceCard from "@/components/glass/GBalanceCard.vue"
import GBalanceGrid from "@/components/glass/GBalanceGrid.vue"
import { leaveBalance } from "@/data/leaves"
import { formatLeaveDays } from "@/utils/formatters"
import { computed, inject } from "vue"

const __ = inject("$translate")

// an empty map {} is truthy — without this check the section renders as a
// bare rule instead of the "no leaves allocated" empty state
const hasBalances = computed(() => leaveBalance.data && Object.keys(leaveBalance.data).length > 0)
// Tile count drives the grid's odd-count layout so 3 (or 5) leave types never
// orphan a cell.
const balanceCount = computed(() =>
	leaveBalance.data ? Object.keys(leaveBalance.data).length : 0
)
</script>
