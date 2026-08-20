<template>
	<BaseLayout :pageTitle="__('My Issues')">
		<template #body>
			<div class="flex flex-col gap-4 px-4 pt-6 pb-8 w-full lg:p-7 max-w-content-column-lg">
				<ResourceError :resource="myIssues" what="your issues" />
				<router-link :to="{ name: 'EmployeeIssueFormView' }" v-slot="{ navigate }">
					<GButton :label="__('Report an Issue')" @click="navigate">
							<template #trailing>
								<svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
									<line x1="5" y1="12" x2="19" y2="12"></line>
									<polyline points="12 5 19 12 12 19"></polyline>
								</svg>
							</template>
						</GButton>
				</router-link>

				<span class="text-eyebrow uppercase text-accent-ink mt-2">{{ __("Reported by you") }}</span>
				<div class="flex flex-col gap-2.5 border-t-2 border-divider pt-4">
					<router-link
						v-for="issue in myIssues.data || []"
						:key="issue.name"
						:to="{ name: 'EmployeeIssueDetailView', params: { id: issue.name } }"
						class="bg-surface border border-divider p-3 cursor-pointer no-underline"
					>
						<div class="flex justify-between items-center mb-1.5">
							<span class="text-caption font-extrabold tracking-wide text-ink-600">
								{{ issue.name }}
							</span>
							<span
								class="text-micro-label font-extrabold uppercase tracking-wider px-2 py-0.5 border"
								:class="STATUS_CHIP[issue.status]"
							>
								{{ __(issue.status) }}
							</span>
						</div>
						<div class="text-card-title font-extrabold text-inkbase mb-0.5">
							{{ __(issue.issue_type) }}
						</div>
						<div class="text-kra-label text-ink-600 truncate">
							{{ dayjs(issue.creation).format("D MMM, HH:mm") }} · {{ issue.details }}
						</div>
					</router-link>

					<EmptyState
						v-if="!myIssues.loading && !myIssues.data?.length"
						:message="__('Nothing reported yet')"
					/>
				</div>
			</div>
		</template>
	</BaseLayout>
</template>

<script setup>
import GButton from "@/components/glass/GButton.vue"
import { createListResource } from "frappe-ui"
import { inject } from "vue"

import BaseLayout from "@/components/BaseLayout.vue"
import ResourceError from "@/components/ResourceError.vue"

const __ = inject("$translate")
const dayjs = inject("$dayjs")
const employee = inject("$employee")

const STATUS_CHIP = {
	Open: "text-amber-700 border-amber-700 dark:text-amber-500 dark:border-amber-500",
	"In Progress": "text-accent-500 border-accent-500 bg-accent-100/40",
	Completed: "text-accent-900 border-transparent bg-accent-200",
}

// row scope already limits staff to their own rows; the explicit filter keeps
// an HR user's "My Issues" personal instead of listing the whole site
const myIssues = createListResource({
	doctype: "Employee Issue",
	filters: { employee: employee.data.name },
	fields: ["name", "issue_type", "urgency", "status", "details", "creation"],
	orderBy: "creation desc",
	pageLength: 50,
	auto: true,
	cache: "hrms:my_issues",
})
</script>
