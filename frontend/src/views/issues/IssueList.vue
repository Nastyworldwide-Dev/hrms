<template>
	<ion-page>
		<ion-content class="ion-padding">
			<div class="flex flex-col h-screen w-screen bg-ground">
				<div class="w-full max-w-[620px] mx-auto">
					<header
						class="flex flex-row bg-ground py-3.5 px-4 items-center justify-between border-b-2 border-divider sticky top-0 z-10"
					>
						<div class="flex flex-row items-center gap-2.5">
							<Button
								variant="ghost"
								class="!pl-0 hover:bg-transparent"
								@click="router.back()"
							>
								<FeatherIcon name="arrow-left" class="h-5 w-5" />
							</Button>
							<h2 class="font-sans font-extrabold text-lg tracking-tight text-inkbase">
								{{ __("My Issues") }}
							</h2>
						</div>
						<router-link :to="{ name: 'EmployeeIssueFormView' }" v-slot="{ navigate }">
							<Button variant="solid" @click="navigate">
								<template #prefix><FeatherIcon name="plus" class="w-4" /></template>
								{{ __("Report") }}
							</Button>
						</router-link>
					</header>

					<div class="flex flex-col gap-2.5 w-full p-4">
						<router-link
							v-for="issue in myIssues.data || []"
							:key="issue.name"
							:to="{ name: 'EmployeeIssueDetailView', params: { id: issue.name } }"
							class="bg-surface border border-divider p-3 cursor-pointer no-underline"
						>
							<div class="flex justify-between items-center mb-1.5">
								<span class="text-[10px] font-extrabold tracking-wide text-ink-600">
									{{ issue.name }}
								</span>
								<span
									class="text-[9px] font-extrabold uppercase tracking-wider px-2 py-0.5 border"
									:class="STATUS_CHIP[issue.status]"
								>
									{{ __(issue.status) }}
								</span>
							</div>
							<div class="text-[13px] font-extrabold text-inkbase mb-0.5">
								{{ __(issue.issue_type) }}
							</div>
							<div class="text-[11px] text-ink-600 truncate">
								{{ dayjs(issue.creation).format("D MMM, HH:mm") }} · {{ issue.details }}
							</div>
						</router-link>

						<EmptyState v-if="!myIssues.loading && !myIssues.data?.length" :message="__('Nothing reported yet')" />
					</div>
				</div>
			</div>
		</ion-content>
	</ion-page>
</template>

<script setup>
import { IonPage, IonContent } from "@ionic/vue"
import { createListResource, FeatherIcon } from "frappe-ui"
import { inject } from "vue"
import { useRouter } from "vue-router"

const __ = inject("$translate")
const dayjs = inject("$dayjs")
const employee = inject("$employee")
const router = useRouter()

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
