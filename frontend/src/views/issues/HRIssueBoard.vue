<template>
	<BaseLayout :pageTitle="__('Issue Board')">
		<template #body>
			<div class="flex flex-col w-full pt-2 pb-8">
				<div class="w-full max-w-content-column-lg lg:mx-0 mx-auto">
					<div class="px-4 pt-4">
						<span class="g-eyebrow">{{ __("HR · People & Culture") }}</span>
					</div>

					<!-- stats: ONE surface with internal dividers (§15.2), not one
					     per tile. The count is dynamic, and the panel is 1 either way. -->
					<div class="px-4 pt-3.5">
						<GStatPanel :columns="statTiles.length === 4 ? 4 : 3">
							<GStatTile
								v-for="stat in statTiles"
								:key="stat.label"
								:value="stat.value"
								:label="stat.label"
							/>
						</GStatPanel>
					</div>

					<!-- search + type filter -->
					<div class="flex gap-2 px-4 pt-2.5">
						<GSearchBar
							v-model="search"
							class="flex-1"
							:placeholder="__('Search name, id, text…')"
							:label="__('Search issues')"
						/>
						<select
							v-model="issueType"
							class="w-[130px] text-sm bg-surface border border-divider p-2 text-inkbase focus:outline-none focus:border-accent-ink"
						>
							<option value="">{{ __("All types") }}</option>
							<option v-for="type in ISSUE_TYPES" :key="type" :value="type">
								{{ __(TYPE_SHORT[type]) }}
							</option>
						</select>
					</div>

					<!-- status tabs: counts stay in the label, so the selected state
					     is never carried by colour alone (§14.1) -->
					<div class="px-4 mt-2.5">
						<GSegmented
							v-model="activeStatus"
							:buttons="statusButtons"
							:label="__('Issue status')"
						/>
					</div>

					<!-- cards -->
					<div class="flex flex-col gap-2.5 w-full p-4">
						<div
							v-for="issue in visibleIssues"
							:key="issue.name"
							class="bg-surface border border-divider p-3 cursor-pointer"
							@click="openIssue(issue.name)"
						>
							<div class="flex justify-between items-center mb-1.5">
								<span class="text-caption font-extrabold tracking-wide text-ink-600">
									{{ issue.name }} · {{ dayjs(issue.creation).format("D MMM, HH:mm") }}
								</span>
								<span
									class="g-eyebrow tracking-wider px-2 py-0.5 border bg-transparent"
									:class="URGENCY_CHIP[issue.urgency]"
								>
									{{ __(issue.urgency) }}
								</span>
							</div>
							<div class="text-card-title font-extrabold text-inkbase mb-0.5">
								{{ issue.employee_name }}
								<span class="text-ink-600 font-semibold">· {{ issue.department || "—" }}</span>
							</div>
							<div class="text-kra-label text-ink-600 truncate">
								<b>{{ __(TYPE_SHORT[issue.issue_type]) }}</b> — {{ issue.details }}
							</div>
						</div>

						<GEmptyState
							v-if="!issues.loading && !visibleIssues.length"
							:title="__('Nothing in {0}', [__(activeStatus).toLowerCase()])"
							:body="__('Issues move here as they are triaged')"
						/>
					</div>
				</div>
			</div>

			<!-- detail sheet -->
			<ion-modal
				:is-open="sheetOpen"
				@didDismiss="sheetOpen = false"
				:initial-breakpoint="1"
				:breakpoints="[0, 1]"
			>
				<ResourceError :resource="detail" what="this issue" />
				<div
					v-if="detail.data"
					class="bg-ground w-full flex flex-col pb-8 max-h-[calc(100vh-5rem)] overflow-y-auto"
				>
					<div class="w-full flex flex-col gap-1 pt-6 pb-3 px-4">
						<div class="g-eyebrow">{{ detail.data.name }}</div>
						<span class="text-inkbase font-extrabold text-screen-title leading-tight">
							{{ detail.data.employee_name }}
						</span>
						<span class="text-xs text-ink-600">
							{{ detail.data.department || "—" }} ·
							{{ dayjs(detail.data.creation).format("D MMM YYYY, HH:mm") }}
						</span>
					</div>

					<div class="grid grid-cols-[110px_1fr] gap-x-3 gap-y-1.5 px-4 text-xs">
						<template v-for="row in detailRows" :key="row.label">
							<div class="g-eyebrow pt-px">
								{{ row.label }}
							</div>
							<div class="text-inkbase" :class="row.classes">{{ row.value }}</div>
						</template>
					</div>

					<div class="px-4 mt-4">
						<label class="text-xs uppercase text-ink-700 tracking-wide font-extrabold">
							{{ __("Status") }}
						</label>
						<div class="flex gap-1.5 mt-1.5">
							<button
								v-for="status in ISSUE_STATUSES"
								:key="status"
								class="g-eyebrow flex-1 py-2 border"
								:class="
									detail.data.status === status
										? 'bg-accent-ink text-ground border-accent-ink'
										: 'bg-surface text-ink-700 border-divider'
								"
								:disabled="saving"
								@click="setStatus(status)"
							>
								{{ __(status) }}
							</button>
						</div>

						<label class="block text-xs uppercase text-ink-700 tracking-wide font-extrabold mt-4">
							{{ __("Internal HR notes") }}
							<span class="text-ink-500 normal-case font-semibold">
								({{ __("never shown to the employee") }})
							</span>
						</label>
						<textarea
							v-model="hrNotes"
							rows="3"
							class="w-full text-sm bg-surface border border-divider p-2 mt-1.5 text-inkbase focus:outline-none focus:border-accent-ink"
							:placeholder="__('Notes for the HR team…')"
						/>
						<Button variant="solid" class="w-full mt-3 py-5" :loading="saving" @click="saveNotes">
							{{ __("Save") }}
						</Button>
					</div>
				</div>
			</ion-modal>
		</template>
	</BaseLayout>
</template>

<script setup>
import GEmptyState from "@/components/glass/GEmptyState.vue"
import GSegmented from "@/components/glass/GSegmented.vue"
import GSearchBar from "@/components/glass/GSearchBar.vue"
import GStatTile from "@/components/glass/GStatTile.vue"
import GStatPanel from "@/components/glass/GStatPanel.vue"
import { IonModal } from "@ionic/vue"
import { createListResource, createResource, toast } from "frappe-ui"
import { computed, inject, ref } from "vue"

import BaseLayout from "@/components/BaseLayout.vue"

import { ISSUE_STATUSES, countByStatus, filterIssues } from "@/utils/issueBoard"

const __ = inject("$translate")
const dayjs = inject("$dayjs")

const ISSUE_TYPES = ["Leave Balance Discrepancy", "Check-in / Check-out Problem", "Other HR Issue"]
// i18n source strings: __("Leave balance"), __("Check-in/out"), __("Other HR")
const TYPE_SHORT = {
	"Leave Balance Discrepancy": "Leave balance",
	"Check-in / Check-out Problem": "Check-in/out",
	"Other HR Issue": "Other HR",
}
const URGENCY_CHIP = {
	High: "text-red-600 border-red-600",
	Medium: "text-amber-700 border-amber-700 dark:text-amber-500 dark:border-amber-500",
	Low: "text-ink-600 border-ink-600",
}

const activeStatus = ref("Open")
const search = ref("")
const issueType = ref("")
const sheetOpen = ref(false)
const hrNotes = ref("")
const saving = ref(false)

const issues = createListResource({
	doctype: "Employee Issue",
	fields: [
		"name",
		"employee",
		"employee_name",
		"department",
		"issue_type",
		"urgency",
		"status",
		"details",
		"creation",
	],
	orderBy: "creation desc",
	pageLength: 500,
	auto: true,
})

// GSegmented takes {key,label}; the count rides in the label so the selected
// state is never signalled by colour alone (§14.1)
const statusButtons = computed(() =>
	ISSUE_STATUSES.map((status) => ({
		key: status,
		label: `${__(status)} (${counts.value?.[status] ?? 0})`,
	}))
)

const counts = computed(() => countByStatus(issues.data))
const visibleIssues = computed(() =>
	filterIssues(issues.data, {
		status: activeStatus.value,
		issueType: issueType.value,
		search: search.value,
	})
)
const statTiles = computed(() => [
	...ISSUE_STATUSES.map((status) => ({
		label: __(status),
		value: counts.value[status],
		classes: "text-inkbase",
	})),
	{ label: __("High urgency"), value: counts.value.high, classes: "text-red-600" },
])

// full doc (incl. permlevel-1 hr_notes, readable by HR) for the sheet
const detail = createResource({
	url: "frappe.client.get",
	transform: (doc) => doc,
	onSuccess(doc) {
		hrNotes.value = doc.hr_notes || ""
	},
	onError(error) {
		console.error("[HRIssueBoard] failed to load issue detail:", error)
		toast({
			title: __("Error"),
			text: __("Could not load the issue"),
			icon: "alert-circle",
			position: "bottom-center",
			iconClasses: "text-red-500",
		})
	},
})

const detailRows = computed(() => {
	const doc = detail.data
	if (!doc) return []
	const rows = [
		{ label: __("Type"), value: __(doc.issue_type) },
		{ label: __("Urgency"), value: __(doc.urgency || "Medium") },
	]
	if (doc.issue_type === "Leave Balance Discrepancy") {
		if (doc.leave_type) rows.push({ label: __("Leave type"), value: doc.leave_type })
		rows.push({
			label: __("Shown / expected"),
			value: `${doc.balance_shown ?? "—"} / ${doc.balance_expected ?? "—"}`,
		})
	}
	if (doc.issue_type === "Check-in / Check-out Problem") {
		if (doc.affected_date)
			rows.push({
				label: __("Affected date"),
				value: dayjs(doc.affected_date).format("D MMM YYYY"),
			})
		if (doc.punch_affected) rows.push({ label: __("Punch"), value: __(doc.punch_affected) })
		if (doc.what_happened) rows.push({ label: __("What happened"), value: __(doc.what_happened) })
	}
	rows.push({ label: __("Details"), value: doc.details, classes: "whitespace-pre-wrap" })
	return rows
})

const openIssue = (name) => {
	console.info("[HRIssueBoard] opening issue:", name)
	detail.fetch({ doctype: "Employee Issue", name })
	sheetOpen.value = true
}

const updateIssue = createResource({
	url: "frappe.client.set_value",
	onError(error) {
		console.error("[HRIssueBoard] failed to update issue:", error)
		toast({
			title: __("Error"),
			text: error.messages?.join(" ") || __("Update failed"),
			icon: "alert-circle",
			position: "bottom-center",
			iconClasses: "text-red-500",
		})
	},
})

const setStatus = async (status) => {
	if (!detail.data || detail.data.status === status) return
	saving.value = true
	try {
		await updateIssue.fetch({
			doctype: "Employee Issue",
			name: detail.data.name,
			fieldname: { status },
		})
		detail.data.status = status
		issues.reload()
		toast({
			title: __("Success"),
			text: __("{0} → {1} — the employee has been notified", [detail.data.name, __(status)]),
			icon: "check-circle",
			position: "bottom-center",
			iconClasses: "text-green-500",
		})
	} finally {
		saving.value = false
	}
}

const saveNotes = async () => {
	if (!detail.data) return
	saving.value = true
	try {
		await updateIssue.fetch({
			doctype: "Employee Issue",
			name: detail.data.name,
			fieldname: { hr_notes: hrNotes.value },
		})
		sheetOpen.value = false
		toast({
			title: __("Success"),
			text: __("Saved"),
			icon: "check-circle",
			position: "bottom-center",
			iconClasses: "text-green-500",
		})
	} finally {
		saving.value = false
	}
}
</script>
