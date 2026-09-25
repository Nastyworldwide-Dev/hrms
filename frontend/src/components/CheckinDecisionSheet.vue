<!--
  Deciding a check-in outside the work area, from the Approvals list
  (AUDIT-PLAN, Approvals row). What the approver needs and nothing else: who,
  when, how far, the photo they took, their reason. Approve is one tap; "Not
  approve" asks why, because the employee reads that reason (P0-10).
  Emits `decided` after the server answers, so the list can reload.
-->
<template>
	<div class="flex flex-col gap-4 px-4 pt-6 pb-8">
		<div class="flex flex-col gap-1">
			<h2 class="text-card-title text-ink">{{ row.who }}</h2>
			<!-- Already in the person's words from the server ("Fri 18 Sep,
			     8:05 am"); parsing it again gave "Invalid Date" (review of 52cc288ef). -->
			<p class="text-caption text-ink-600">{{ row.when }}</p>
			<p class="text-caption text-ink-600">{{ row.detail }}</p>
		</div>

		<a
			v-if="row.selfie_image"
			:href="row.selfie_image"
			target="_blank"
			rel="noopener"
			class="block"
		>
			<img
				:src="row.selfie_image"
				:alt="__('Check-in photo')"
				class="w-full max-h-64 object-cover rounded-panel"
				loading="lazy"
			/>
		</a>

		<p class="text-card-title font-normal text-ink">
			{{ row.reason || __("No reason given.") }}
		</p>

		<div class="flex flex-row gap-3">
			<GGhostButton class="flex-1" :label="__('Not approve')" @click="askingWhy = true" />
			<GButton class="flex-1" :label="__('Approve')" :pending="submitting" @click="approve" />
		</div>

		<GConfirm
			:is-open="askingWhy"
			:title="__('Not approve this check-in?')"
			:confirm-label="__('Not approve')"
			:cancel-label="__('Keep')"
			:confirm-disabled="!reason.trim()"
			:pending="submitting"
			destructive
			@confirm="reject"
			@cancel="askingWhy = false"
		>
			{{ __("The employee sees your reason.") }}
			<template #extra>
				<GTextarea v-model="reason" :label="__('Why not? (required)')" />
			</template>
		</GConfirm>
	</div>
</template>

<script setup>
import { inject, ref } from "vue"
import { gToast } from "@/components/glass/toast"

import GButton from "@/components/glass/GButton.vue"
import GConfirm from "@/components/glass/GConfirm.vue"
import GGhostButton from "@/components/glass/GGhostButton.vue"
import GTextarea from "@/components/glass/GTextarea.vue"
import { approveResource, pendingCountResource, rejectResource } from "@/data/remoteCheckin"
import { decisionToast } from "@/utils/approvalToast"
import { firstMessage } from "@/utils/loudRequest"

const props = defineProps({
	row: { type: Object, required: true },
})
const emit = defineEmits(["decided"])

const __ = inject("$translate")

const reason = ref("")
const askingWhy = ref(false)
const submitting = ref(false)

async function decide(kind, submit) {
	submitting.value = true
	try {
		const result = await submit()
		const shown = decisionToast(kind, result?.attendance_repair, __)
		gToast({
			title: shown.title,
			text: shown.text,
			// "Approved, but attendance was not updated" is a warning, not news.
			variant: shown.tone,
		})
		console.info("[CheckinDecisionSheet] decided", kind)
		askingWhy.value = false
		pendingCountResource.reload()
		emit("decided")
	} catch (err) {
		console.error("[CheckinDecisionSheet] decision failed:", err)
		gToast({
			title: __("Could not save"),
			text: firstMessage(err, __("Try again.")),
			variant: "error",
		})
	} finally {
		submitting.value = false
	}
}

const approve = () =>
	decide("approve", () =>
		approveResource.submit({
			request: props.row.name,
		})
	)

const reject = () =>
	decide("reject", () =>
		rejectResource.submit({
			request: props.row.name,
			approver_remarks: reason.value.trim(),
		})
	)
</script>
