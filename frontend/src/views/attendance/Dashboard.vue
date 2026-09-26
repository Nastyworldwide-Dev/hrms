<template>
	<BaseLayout :pageTitle="__('Calendar')">
		<template #body>
			<!-- The month, and the one thing each day needs (approved Calendar
			     plan, docs/glass/plan/pages/01-calendar.md). The overtime card, the
			     count strip and the three "start a request" rows are gone: the
			     claim list lives on Requests, the grid already shows the counts,
			     and a day's own fix starts from its day sheet. -->
			<div
				class="flex flex-col px-4 pt-6 pb-8 gap-5 w-full max-w-content-column-lg mx-auto lg:py-7"
			>
				<AttendanceCalendar ref="calendar" />
				<ResourceError :resource="shifts" what="your shifts" />

				<!-- Two destinations, used now and then: list rows with a chevron
				     (HIG Lists and tables), not underlined web links (alpha.6 C5). -->
				<GListPanel>
					<GListRow
						:label="__('All check-ins')"
						@click="router.push({ name: 'EmployeeCheckinListView' })"
					/>
					<GListRow
						:label="__('Your shifts')"
						@click="router.push({ name: 'ShiftAssignmentListView' })"
					/>
				</GListPanel>
			</div>
		</template>
	</BaseLayout>
</template>

<script setup>
import { personalCacheKey } from "@/utils/personalCache"
import { createResource } from "frappe-ui"
import { ref } from "vue"
import { onIonViewWillEnter } from "@ionic/vue"
import AttendanceCalendar from "@/components/AttendanceCalendar.vue"

import BaseLayout from "@/components/BaseLayout.vue"
import GListPanel from "@/components/glass/GListPanel.vue"
import GListRow from "@/components/glass/GListRow.vue"
import { useRouter } from "vue-router"
import ResourceError from "@/components/ResourceError.vue"

const router = useRouter()

// The calendar stays mounted while the tab is in the Ionic stack, so a day
// the hourly job processed while the employee was on another tab never
// showed until a full reload. Re-entering the view refreshes the month.
const calendar = ref(null)
onIonViewWillEnter(() => calendar.value?.refresh?.())

// Still fetched, and only so the screen can SAY when shifts cannot be read —
// a silent failure here is an employee who thinks they have no shift.
const shifts = createResource({
	url: "hrms.api.get_shifts",
	auto: true,
	cache: personalCacheKey("hrms:shifts"),
})
</script>
