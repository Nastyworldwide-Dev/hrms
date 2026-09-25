<template>
	<!-- body only: the page chrome (header "Helpdesk" + the HR Issues / IT
	     Helpdesk pills) belongs to views/helpdesk/HelpdeskHub.vue since 15 Sep
	     2026. Who sees this board is unchanged: IssuesTab.vue picks it by role,
	     and server row scope is the real fence. -->
	<div>
		<div class="flex flex-col w-full pt-2 pb-8">
			<!-- same column as the pill row above it (centred, lg:px-7 = px-4 + lg:px-3) -->
			<div class="w-full max-w-content-column-lg mx-auto lg:px-3">
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
					<GSelect
						class="w-32"
						:options="ISSUE_TYPES.map((type) => ({ value: type, label: __(TYPE_SHORT[type]) }))"
						:model-value="issueType"
						:placeholder="__('All types')"
						:aria-label="__('Issue type')"
						@update:model-value="(v) => (issueType = v)"
					/>
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
					<button
						v-for="issue in visibleIssues"
						:key="issue.name"
						type="button"
						class="g-focusable block w-full text-left bg-surface border border-divider p-3 cursor-pointer"
						@click="openIssue(issue.name)"
					>
						<span class="flex justify-between items-center mb-1.5">
							<span class="text-caption font-bold tracking-wide text-ink-600">
								{{ issue.name }} · {{ dayjs(issue.creation).format("D MMM, HH:mm") }}
							</span>
							<span
								class="g-eyebrow tracking-wider px-2 py-0.5 border bg-transparent"
								:class="URGENCY_CHIP[issue.urgency]"
							>
								{{ __(issue.urgency) }}
							</span>
						</span>
						<span class="block text-card-title font-bold text-inkbase mb-0.5">
							{{ issue.employee_name }}
							<span class="text-ink-600 font-semibold"
								>· {{ departmentLabel(issue.department) || "—" }}</span
							>
						</span>
						<span class="block text-kra-label text-ink-600 truncate">
							<b>{{ __(TYPE_SHORT[issue.issue_type]) }}</b> — {{ issue.details }}
						</span>
					</button>

					<ResourceError v-if="issues.error" :resource="issues" :what="__('the issue board')" />
					<GEmptyState
						v-else-if="!issues.loading && !visibleIssues.length"
						:title="__('Nothing in {0}', [__(activeStatus).toLowerCase()])"
						:body="__('Issues move here as they are triaged')"
					/>
				</div>
			</div>
		</div>

		<!-- detail sheet -->
		<GModal
			:is-open="sheetOpen"
			:title="detail.data?.employee_name || __('Issue')"
			@did-dismiss="sheetOpen = false"
		>
			<ResourceError :resource="detail" what="this issue" />
			<div v-if="detail.data" class="w-full flex flex-col pb-8">
				<div class="w-full flex flex-col gap-1 pb-3 px-4">
					<div class="g-eyebrow">{{ detail.data.name }}</div>
					<span class="text-xs text-ink-600">
						{{ departmentLabel(detail.data.department) || "—" }} ·
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

				<!-- On the kit (owner, 25 Sep 2026: hand-rolled screens). -->
				<div class="g-form-body">
					<section class="g-form-section">
						<h2 class="g-form-section__title">{{ __("Status") }}</h2>
						<GSegmented
							:buttons="ISSUE_STATUSES.map((status) => ({ key: status, label: __(status) }))"
							:model-value="detail.data.status"
							:label="__('Status')"
							@update:model-value="(status) => !saving && setStatus(status)"
						/>
					</section>
					<section class="g-form-section">
						<div class="g-form-group">
							<div class="g-form-row g-form-row--stacked">
								<span class="g-form-row__label">{{ __("Internal HR notes") }}</span>
								<GTextarea v-model="hrNotes" :aria-label="__('Internal HR notes')" :placeholder="__('Notes for the HR team…')" />
							</div>
						</div>
						<p class="g-form-footer">{{ __("Never shown to the employee.") }}</p>
					</section>
					<GButton :label="__('Save')" :pending="saving" @click="saveNotes" />
				</div>
			</div>
		</GModal>
	</div>
</template>

<script setup>
import { departmentLabel } from "@/utils/departmentLabel"
import GEmptyState from "@/components/glass/GEmptyState.vue"
import GSegmented from "@/components/glass/GSegmented.vue"
import GSearchBar from "@/components/glass/GSearchBar.vue"
import GStatTile from "@/components/glass/GStatTile.vue"
import GStatPanel from "@/components/glass/GStatPanel.vue"
import GModal from "@/components/glass/GModal.vue"
import GButton from "@/components/glass/GButton.vue"
import GSelect from "@/components/glass/GSelect.vue"
import GTextarea from "@/components/glass/GTextarea.vue"
import { createListResource, createResource } from "frappe-ui"
import { gToast } from "@/components/glass/toast"
import { computed, inject, ref } from "vue"

import { ISSUE_STATUSES, countByStatus, filterIssues } from "@/utils/issueBoard"
import { firstMessage } from "@/utils/loudRequest"

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
		gToast({
			title: __("Error"),
			text: __("Could not load the issue: {0}", [firstMessage(error)]),
			variant: "error",
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
		gToast({
			title: __("Error"),
			text: firstMessage(error, __("Update failed")),
			variant: "error",
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
		gToast({
			title: __("Success"),
			text: __("{0} → {1} — the employee has been notified", [detail.data.name, __(status)]),
			variant: "success",
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
		gToast({
			title: __("Success"),
			text: __("Saved"),
			variant: "success",
		})
	} finally {
		saving.value = false
	}
}
</script>
