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

				<span class="g-eyebrow mt-2">{{ __("Reported by you") }}</span>
				<div class="flex flex-col gap-2.5 pt-1">
					<!-- §15.1/§15.2: a LIST of issues is unbounded, and N glass cards
					     are N surfaces — an employee with eight open tickets would
					     blow the budget of 6 on its own. So the list flattens to ONE
					     panel, exactly as the balance grid and stat row do.
					     GIssueCard stays for the dashboard context, where §15.2
					     counts a bounded two or three. -->
					<GListPanel v-if="myIssues.loading || myIssues.data?.length" :loading="myIssues.loading">
						<GListRow
							v-for="issue in myIssues.data || []"
							:key="issue.name"
							:label="__(issue.issue_type) || __('Issue')"
							:sublabel="issueMeta(issue)"
							@click="router.push({ name: 'EmployeeIssueDetailView', params: { id: issue.name } })"
						>
							<template #badge>
								<GStatusChip :status="issue.status" :label="__(issue.status)" />
							</template>
						</GListRow>
					</GListPanel>

					<!-- §11.1 -->
					<GEmptyState
						v-if="!myIssues.loading && !myIssues.data?.length"
						:title="__('Nothing reported')"
						:body="__('If something looks wrong, tell us — a screenshot helps')"
					/>
				</div>
			</div>
		</template>
	</BaseLayout>
</template>

<script setup>
import GListRow from "@/components/glass/GListRow.vue"
import GListPanel from "@/components/glass/GListPanel.vue"
import GEmptyState from "@/components/glass/GEmptyState.vue"
import GStatusChip from "@/components/glass/GStatusChip.vue"
import { useRouter } from "vue-router"
import GButton from "@/components/glass/GButton.vue"
import { createListResource } from "frappe-ui"
import { inject } from "vue"

import BaseLayout from "@/components/BaseLayout.vue"
import ResourceError from "@/components/ResourceError.vue"

const router = useRouter()
const __ = inject("$translate")
const dayjs = inject("$dayjs")
const employee = inject("$employee")


// row scope already limits staff to their own rows; the explicit filter keeps
// an HR user's "My Issues" personal instead of listing the whole site
// An unset optional field interpolated into a template literal renders the
// LITERAL STRING "null" in the row — which is what shipped: every issue row
// read "HR-ISS-26-08-00002 · 21 Aug, 07:51 · null". Build the meta line from
// the parts that actually have a value.
function issueMeta(issue) {
	const when = issue.creation ? dayjs(issue.creation).format("D MMM, HH:mm") : ""
	return [issue.name, when, issue.details].filter(Boolean).join(" · ")
}

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
