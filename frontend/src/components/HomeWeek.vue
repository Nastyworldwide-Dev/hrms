<!--
  HomeWeek — "This week" on Home (owner-approved Home, 23 Sep 2026).

  One row: "4 days worked · 1h 30m overtime to claim ›", tapping to the OT
  form. ALWAYS renders: a skeleton on first load, one plain line if the call
  fails, and "Nothing to claim this week." when there is no overtime waiting —
  a block that vanished read as a broken Home.

  The overtime figure is the Requests screen's own (server reuses
  requests_summary._overtime), so the two screens cannot disagree.
-->
<template>
	<div class="w-full">
		<div class="g-eyebrow mb-4">{{ __("This week") }}</div>
		<p v-if="homeWeek.error" class="text-caption text-ink-600">
			{{ __("This week could not be loaded. Pull down to try again.") }}
		</p>
		<GListPanel v-else :loading="homeWeek.loading && !homeWeek.data" :rows="1">
			<GListRow :label="daysLine" :sublabel="claimLine" :tappable="hasOvertime" @click="claim">
				<template #icon>
					<CalendarCheck class="g-row-icon" />
				</template>
			</GListRow>
		</GListPanel>
	</div>
</template>

<script setup>
import { computed, inject, onMounted } from "vue"
import { useRouter } from "vue-router"
import { CalendarCheck } from "lucide-vue-next"

import GListPanel from "@/components/glass/GListPanel.vue"
import GListRow from "@/components/glass/GListRow.vue"

import { homeWeek } from "@/data/home"
import { hoursAsTime } from "@/utils/daySheet"

const __ = inject("$translate")
const router = useRouter()

const days = computed(() => Number(homeWeek.data?.days_worked) || 0)
const overtime = computed(() => Number(homeWeek.data?.overtime_hours) || 0)
const hasOvertime = computed(() => Boolean(hoursAsTime(overtime.value)))

const daysLine = computed(() =>
	days.value === 1 ? __("1 day worked") : __("{0} days worked", [days.value])
)
const claimLine = computed(() =>
	hasOvertime.value
		? __("{0} overtime to claim", [hoursAsTime(overtime.value)])
		: __("Nothing to claim this week.")
)

function claim() {
	console.info("[HomeWeek] open OT form", { hours: overtime.value })
	router.push({ name: "OTRequestFormView" })
}

onMounted(() => {
	homeWeek.fetch()
})
</script>
