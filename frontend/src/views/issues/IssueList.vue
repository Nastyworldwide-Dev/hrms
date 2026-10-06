<template>
	<!-- body only: the page chrome (header, HR / IT pills, Who to ask and the
	     one "Report an issue" button) belongs to views/helpdesk/HelpdeskHub.vue -->
	<div class="flex flex-col gap-4 px-4 pt-4 w-full max-w-content-column-lg mx-auto">
		<GPullRefresh @refresh="refresh" />
		<ResourceError :resource="myIssues" what="your HR issues" />
		<HelpSplitList
			:rows="myIssues.data || []"
			:loading="myIssues.loading && !myIssues.data"
			:title="(issue) => __(issue.issue_type) || __('Issue')"
			:chip-label="(status) => __(status)"
			:empty-body="__('Something wrong with your pay, leave or records? Tap Report an issue below.')"
			@open="openIssue"
		/>
	</div>
</template>

<script setup>
import { personalCacheKey } from "@/utils/personalCache"
import { useRouter } from "vue-router"
import { createListResource } from "frappe-ui"
import { defineAsyncComponent, inject } from "vue"

import HelpSplitList from "@/components/HelpSplitList.vue"
import ResourceError from "@/components/ResourceError.vue"

const router = useRouter()
const __ = inject("$translate")
const employee = inject("$employee")

function openIssue(issue) {
	console.info("[IssueList] open issue", issue.name)
	router.push({ name: "EmployeeIssueDetailView", params: { id: issue.name } })
}

// row scope already limits staff to their own rows; the explicit filter keeps
// an HR user's "My Issues" personal instead of listing the whole site
const myIssues = createListResource({
	doctype: "Employee Issue",
	filters: { employee: employee.data?.name },
	fields: ["name", "issue_type", "status", "creation", "modified"],
	orderBy: "creation desc",
	pageLength: 50,
	auto: true,
	cache: personalCacheKey("hrms:my_issues"),
})

//: Loaded on first use, not in the first download (alpha.13: Ionic's
//: refresher is 41 KB, and nobody pulls before the page has drawn).
const GPullRefresh = defineAsyncComponent(() => import("@/components/glass/GPullRefresh.vue"))

//: Pull to refresh reloads the issues drawn here (6 Oct 2026: a pull did nothing).
//: This list has no ion-content of its own: it sits in the help page's, whose own
//: pull (HelpdeskHub) is drawn only for the IT pill, so a pull is never answered twice.
async function refresh(event) {
	console.info("[IssueList] pull-to-refresh")
	await Promise.allSettled([myIssues.reload()])
	event.target?.complete?.()
}
</script>
