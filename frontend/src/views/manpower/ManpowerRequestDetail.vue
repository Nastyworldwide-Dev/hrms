<!--
  One manpower request: where it stands, the PROGRESS tracker (Sent, Manager, HR, Filled; who and
  when), the answers, and Withdraw for the sender while the server still allows it. The approver,
  who reads it through the share, sees the same page without Withdraw. Not a chat: no comment box
  (owner, 22 Oct 2026). Rules and words live in utils/manpowerRequest.js.

  Every step is a shape AND a word, never colour alone (RequestTimeline's rule).
-->
<template>
	<GPage>
		<ion-content :fullscreen="true">
			<div class="flex flex-col h-full w-full form-view-root">
				<ShellHeader bare :title="__('Manpower request')" />
				<div class="grow overflow-y-auto" tabindex="0" :aria-label="__('Manpower request')">
					<div class="w-full max-w-content-column-lg mx-auto flex flex-col gap-5 px-4 pt-4 pb-8">
						<ResourceError :resource="request" back :what="__('this manpower request')" />

						<template v-if="doc">
							<section class="g-form-section">
								<div class="g-form-group">
									<div class="g-form-row g-form-row--readonly">
										<span class="g-form-row__label">{{ __("Status") }}</span>
										<GStatusChip :status="where.status" :label="__(where.label)" />
									</div>
									<div
										v-for="row in summary"
										:key="row.label"
										class="g-form-row g-form-row--readonly"
									>
										<span class="g-form-row__label">{{ row.label }}</span>
										<span class="g-form-row__value">{{ row.value }}</span>
									</div>
								</div>
							</section>

							<!-- Progress -->
							<section class="g-form-section">
								<h2 class="g-form-section__title">{{ __("Progress") }}</h2>
								<ResourceError :resource="progress" :what="__('the progress')" />
								<ol v-if="rows.length" class="g-form-group mp-steps" :aria-label="__('Progress')">
									<li
										v-for="row in rows"
										:key="row.key"
										class="mp-step"
										:class="`mp-step--${row.state}`"
									>
										<span class="mp-mark" aria-hidden="true">
											<Check v-if="row.shape === 'check'" class="h-3.5 w-3.5" />
											<X v-else-if="row.shape === 'cross'" class="h-3.5 w-3.5" />
											<Minus v-else-if="row.shape === 'dash'" class="h-3.5 w-3.5" />
										</span>
										<div class="min-w-0">
											<div class="font-semibold">{{ row.title }}</div>
											<div v-if="row.line" class="text-sm text-ink-600">{{ row.line }}</div>
											<div v-if="row.note" class="mp-note">{{ row.note }}</div>
										</div>
									</li>
								</ol>
								<GSkeleton v-else-if="progress.loading" height="96px" />
							</section>

							<!-- All answers -->
							<section class="g-form-section">
								<div class="g-form-group">
									<button
										type="button"
										class="g-form-row g-form-row--action g-focusable"
										:aria-expanded="showAnswers"
										@click="showAnswers = !showAnswers"
									>
										<span class="g-form-row__label">{{ __("All answers") }}</span>
										<ChevronDown
											class="h-4 w-4 flex-none"
											:class="showAnswers ? '' : '-rotate-90'"
											aria-hidden="true"
										/>
									</button>
									<template v-if="showAnswers">
										<div
											v-for="row in answers"
											:key="row.label"
											class="g-form-row g-form-row--stacked g-form-row--readonly"
										>
											<span class="g-form-row__label">{{ row.label }}</span>
											<span class="g-form-row__value g-request-sheet__text">{{
												row.value || __("Not answered")
											}}</span>
										</div>
									</template>
								</div>
							</section>

							<p v-if="doc.status === 'Rejected'" class="g-form-footer">
								{{ __("You can send a new request with changes.") }}
							</p>

							<!-- Withdraw: the sender only, while the server allows it -->
							<section v-if="offerWithdraw" class="flex flex-col gap-2">
								<GButton :label="__('Withdraw request')" danger @click="askWithdraw" />
								<p class="g-form-footer text-center">{{ told }}</p>
							</section>
						</template>
						<GSkeleton v-else-if="request.loading" height="160px" />
					</div>
				</div>
			</div>

			<GConfirm
				:is-open="confirmOpen"
				:title="__('Withdraw this request?')"
				:confirm-label="__('Withdraw')"
				destructive
				@confirm="withdrawNow"
				@cancel="confirmOpen = false"
			>
				{{ told }}
				<template #extra>
					<div class="g-form-group">
						<FormField
							fieldtype="Small Text"
							:label="__('Reason')"
							:placeholder="__('Optional. For example: the role is covered now')"
							v-model="reason"
						/>
					</div>
				</template>
			</GConfirm>
		</ion-content>
	</GPage>
</template>

<script setup>
import { IonContent } from "@ionic/vue"
import { Check, ChevronDown, Minus, X } from "lucide-vue-next"
import { createResource } from "frappe-ui"
import { computed, inject, onBeforeUnmount, ref } from "vue"

import FormField from "@/components/FormField.vue"
import ResourceError from "@/components/ResourceError.vue"
import ShellHeader from "@/components/ShellHeader.vue"
import GButton from "@/components/glass/GButton.vue"
import GConfirm from "@/components/glass/GConfirm.vue"
import GPage from "@/components/glass/GPage.vue"
import GSkeleton from "@/components/glass/GSkeleton.vue"
import GStatusChip from "@/components/glass/GStatusChip.vue"
import { gToast } from "@/components/glass/toast"
import { hideRequest, unhideRequest } from "@/data/hiddenRequests"
import { reloadRequestLists } from "@/data/requestLists"
import { showUndo } from "@/data/undoBar"
import { departmentLabel } from "@/utils/departmentLabel"
import { firstMessage } from "@/utils/loudRequest"
import {
	DOCTYPE,
	canWithdraw,
	detailKind,
	optimisticWithdrawn,
	stage,
	trackerRows,
} from "@/utils/manpowerRequest"
import { siteTime } from "@/utils/siteTime"
import { undoable } from "@/utils/undoable"
import dayjs from "dayjs"

const props = defineProps({ id: { type: String, required: true } })

const __ = inject("$translate")
const employee = inject("$employee")

const request = createResource({
	url: "frappe.client.get",
	params: { doctype: DOCTYPE, name: props.id },
	auto: true,
})
const doc = computed(() => request.data)
const progress = createResource({
	url: "hrms.api.manpower.get_progress",
	params: { name: props.id },
	auto: true,
})

const where = computed(() => stage(doc.value))
// What the tracker shows right now; a withdraw shows at once and Undo puts the old steps back.
const shownSteps = ref(null)
const when = (at) => {
	const time = siteTime(at)
	return time.isValid() ? time.format("D MMM, h:mm a") : ""
}
const rows = computed(() => trackerRows(shownSteps.value || progress.data || [], { t: __, when }))

const sentence = (text) => (text ? String(text) : "")
const summary = computed(() => {
	const d = doc.value
	return [
		{ label: __("Position"), value: d.position_title },
		{ label: __("People needed"), value: String(d.headcount) },
		{ label: __("Department"), value: departmentLabel(d.department) },
		{ label: __("This is"), value: detailKind(d, __) },
		{ label: __("Urgency"), value: d.urgency ? __(d.urgency) : "" },
		{
			label: __("Target start"),
			value: d.start_date ? dayjs(d.start_date).format("D MMM YYYY") : __("Not fixed"),
		},
	].filter((row) => row.value)
})
const showAnswers = ref(false)
const answers = computed(() => {
	const d = doc.value
	const money = (n) => `RM ${Number(n || 0).toLocaleString("en-MY")}`
	return [
		{ label: __("How soon"), value: d.how_soon },
		{ label: __("Reason"), value: sentence(d.justification) },
		{ label: __("Band"), value: d.band },
		{ label: __("Budgeted"), value: money(d.budgeted_salary) },
		{ label: __("Proposed"), value: money(d.proposed_salary) },
		{
			label: __("Location"),
			value: d.location || (d.location_other ? `${__("Other")}: ${d.location_other}` : ""),
		},
		...(d.answers || []).map((a) => ({ label: a.question, value: sentence(a.answer) })),
	]
})

// ---- Withdraw
const offerWithdraw = computed(() => canWithdraw(doc.value, employee.data?.name))
//: who is told: the approver while it waits on them, HR always (the server does the telling)
const told = computed(() => {
	const approver = rows.value.find((row) => row.key === "manager" && row.state === "current")
	const name = progress.data?.find((s) => s.key === "manager" && s.state === "current")?.who
	return approver && name ? __("{0} and HR will be told.", [name]) : __("HR will be told.")
})
const confirmOpen = ref(false)
const reason = ref("")
const withdraw = createResource({ url: "hrms.api.manpower.withdraw" })
let pending = null

function askWithdraw() {
	reason.value = ""
	confirmOpen.value = true
}
function withdrawNow() {
	confirmOpen.value = false
	const note = reason.value.trim()
	const before = { doc: { ...doc.value }, steps: shownSteps.value }
	// shown at once; the server is asked when the Undo window closes (utils/undoable)
	shownSteps.value = optimisticWithdrawn(progress.data || [], {
		who: employee.data?.employee_name || "",
		at: dayjs().format("YYYY-MM-DD HH:mm:ss"),
		note,
	})
	request.data = { ...doc.value, status: "Withdrawn" }
	hideRequest(props.id)
	const restore = () => {
		shownSteps.value = before.steps
		request.data = before.doc
		unhideRequest(props.id)
	}
	pending = undoable(() =>
		withdraw.submit(
			{ name: props.id, reason: note },
			{
				onSuccess() {
					reloadRequestLists("manpower withdrawn")
					unhideRequest(props.id)
					shownSteps.value = null
					request.reload()
					progress.reload()
				},
				onError(error) {
					// it could not be withdrawn: it comes back, and says why
					restore()
					gToast({
						title: __("Not withdrawn"),
						text: firstMessage(error, __("Could not withdraw the request.")),
						variant: "error",
					})
				},
			}
		)
	)
	showUndo(__("Request withdrawn"), pending, restore)
}
// leaving the page runs a waiting withdraw at once, so it is never lost
onBeforeUnmount(() => pending?.flush())
</script>

<style scoped>
.mp-steps {
	list-style: none;
	margin: 0;
	padding: 4px 16px;
}
.mp-step {
	display: flex;
	gap: 12px;
	padding: 10px 0;
}
.mp-mark {
	flex: none;
	width: 22px;
	height: 22px;
	margin-top: 1px;
	border-radius: 50%;
	display: inline-flex;
	align-items: center;
	justify-content: center;
	border: 2px solid var(--g-ink3);
	color: var(--g-on-brand);
}
.mp-step--done .mp-mark {
	background: var(--g-success-ink);
	border-color: var(--g-success-ink);
	color: #fff;
}
.mp-step--current .mp-mark {
	border-color: var(--g-accent-ink);
	background: radial-gradient(circle, var(--g-accent-ink) 40%, transparent 45%);
}
.mp-step--rejected .mp-mark {
	background: var(--g-danger-ink);
	border-color: var(--g-danger-ink);
	color: #fff;
}
.mp-step--withdrawn .mp-mark {
	background: var(--g-ink2);
	border-color: var(--g-ink2);
	color: #fff;
}
.mp-note {
	margin-top: 4px;
	padding: 6px 10px;
	border-radius: 8px;
	background: var(--g-track-solid);
	font-size: 0.875rem;
}
</style>
