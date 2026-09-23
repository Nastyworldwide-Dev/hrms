<template>
	<BaseLayout :pageTitle="__('Calendar')">
		<template #body>
			<!-- The month, and the one thing each day needs (approved Calendar
			     plan, docs/glass/plan/pages/01-calendar.md). The overtime card, the
			     count strip and the three "start a request" rows are gone: the
			     claim list lives on Requests, the grid already shows the counts,
			     and a day's own fix starts from its day sheet. -->
			<div
				class="flex flex-col px-4 pt-6 pb-8 gap-5 w-full max-w-content-column-lg mx-auto lg:p-7"
			>
				<AttendanceCalendar ref="calendar" />
				<ResourceError :resource="shifts" what="your shifts" />

				<!-- Two quiet links: used now and then, one tap away. -->
				<div class="flex flex-row flex-wrap gap-x-6 gap-y-2 text-card-title">
					<router-link
						:to="{ name: 'EmployeeCheckinListView' }"
						class="g-focusable g-seclink underline underline-offset-link text-ink-800"
						>{{ __("All check-ins") }}</router-link
					>
					<router-link
						:to="{ name: 'ShiftAssignmentListView' }"
						class="g-focusable g-seclink underline underline-offset-link text-ink-800"
						>{{ __("Your shifts") }}</router-link
					>
				</div>
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
import ResourceError from "@/components/ResourceError.vue"

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
