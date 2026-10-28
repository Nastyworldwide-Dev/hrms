<template>
	<GPage>
		<ListView
			doctype="Manpower Request"
			:pageTitle="__('Manpower requests')"
			:fields="MANPOWER_LIST_FIELDS"
			:filterConfig="FILTER_CONFIG"
		>
			<!-- A draft kept on this phone is not a request yet: it sits first, marked Draft. -->
			<template #beforeList>
				<GListPanel v-if="draft" class="mt-5">
					<GListRow
						:label="draft.model?.position_title || __('No title yet')"
						:sublabel="__('Draft · step {0} of {1}', [draftStep, STEPS.length])"
						:tint="TILE.sop"
						@click="router.push({ name: 'ManpowerRequestFormView' })"
					>
						<template #icon><Users class="g-row-icon" /></template>
						<template #badge><GStatusChip status="draft" :label="__('Draft')" /></template>
					</GListRow>
				</GListPanel>
			</template>
		</ListView>
	</GPage>
</template>

<script setup>
import { Users } from "lucide-vue-next"
import { computed, inject } from "vue"
import { useRouter } from "vue-router"

import ListView from "@/components/ListView.vue"
import GListPanel from "@/components/glass/GListPanel.vue"
import GListRow from "@/components/glass/GListRow.vue"
import GPage from "@/components/glass/GPage.vue"
import GStatusChip from "@/components/glass/GStatusChip.vue"
import { MANPOWER_LIST_FIELDS } from "@/data/manpower"
import { TILE } from "@/utils/iconTile"
import { STAGE_LABELS, STEPS, readDraft } from "@/utils/manpowerRequest"
import { sessionUser } from "@/utils/personalCache"

const __ = inject("$translate")
const router = useRouter()

const draft = readDraft(sessionUser())
const draftStep = computed(() => Math.min((Number(draft?.step) || 0) + 1, STEPS.length))

const FILTER_CONFIG = [
	{
		fieldname: "status",
		fieldtype: "Select",
		label: __("Status"),
		options: [
			{ label: __(STAGE_LABELS[0]), value: "Open" },
			{ label: __(STAGE_LABELS[1]), value: "Approved" },
			{ label: __("Rejected"), value: "Rejected" },
			{ label: __("Withdrawn"), value: "Withdrawn" },
		],
	},
	{
		fieldname: "urgency",
		fieldtype: "Select",
		label: __("Urgency"),
		options: [
			{ label: __("High"), value: "High" },
			{ label: __("Medium"), value: "Medium" },
			{ label: __("Low"), value: "Low" },
		],
	},
	{ fieldname: "department", fieldtype: "Link", label: __("Department"), options: "Department" },
]
</script>
