<!--
  Ask for staff, six steps (owner-approved mockup, 22 Oct 2026): Position, Type, Why, Pay,
  Requirements, Review. Every rule (what blocks Next and why, the Other site, the replacement
  list, the insert) lives in utils/manpowerRequest.js and is tested there; this file draws it.

  Next is dimmed WITH its reason shown above it and linked to it (aria-describedby), so nobody
  taps a dead button to find out why (the blocked-Send rule, UX review 21 Oct 2026). Every state
  that dims it is the one `blocker` below. Answers are kept on Back. Leaving part-way offers
  "Keep as draft": kept on this phone only, because an Open request goes to the approver.
-->
<template>
	<GPage>
		<ion-content :fullscreen="true">
			<div class="flex flex-col h-full w-full form-view-root">
				<ShellHeader bare :title="__('Manpower request')" :back="askToLeave" />

				<GEmptyState
					v-if="cannotRequest"
					class="mt-8"
					:icon="Users"
					:title="__('Only people with a team can ask for staff')"
					:body="__('Ask your manager, or HR, to send this request.')"
				/>

				<div v-else class="grow flex min-h-0 w-full max-w-content-column-lg mx-auto">
					<!-- desktop: the steps down the side, as the mockup draws them -->
					<nav class="hidden lg:block w-48 flex-none pt-6 pr-4" :aria-label="__('Steps')">
						<ol class="flex flex-col gap-1">
							<li v-for="(s, i) in STEPS" :key="s.key">
								<button
									type="button"
									class="g-focusable w-full text-left py-2 px-3 rounded-lg text-ink-700"
									:class="i === step ? 'font-semibold bg-surface' : ''"
									:aria-current="i === step ? 'step' : undefined"
									:disabled="i > furthest"
									@click="goTo(i)"
								>
									{{ i + 1 }}. {{ __(s.title) }}
								</button>
							</li>
						</ol>
					</nav>

					<div class="grow flex flex-col min-w-0">
						<div class="px-4 pt-3">
							<b>{{ __("Step {0} of {1}", [step + 1, STEPS.length]) }}</b>
							<div
								class="mp-track"
								role="progressbar"
								:aria-label="__('Progress')"
								aria-valuemin="1"
								:aria-valuemax="STEPS.length"
								:aria-valuenow="step + 1"
							>
								<div
									class="mp-fill"
									:style="{ transform: `scaleX(${(step + 1) / STEPS.length})` }"
								/>
							</div>
						</div>

						<div
							ref="scroller"
							class="grow overflow-y-auto"
							tabindex="0"
							:aria-label="__(STEPS[step].title)"
						>
							<div class="flex flex-col gap-6 px-4 pt-4 pb-6">
								<div>
									<h2 class="text-xl font-semibold">{{ __(STEPS[step].title) }}</h2>
									<p class="text-ink-600">{{ __(STEPS[step].sub) }}</p>
								</div>

								<!-- 1 Position -->
								<section v-if="step === 0" class="g-form-section">
									<div class="g-form-group">
										<FormField
											fieldtype="Data"
											:label="__('Position title')"
											reqd
											:placeholder="__('Type here')"
											v-model="model.position_title"
											:error-message="shown('position_title')"
										/>
										<div class="g-form-row" :class="{ 'g-form-row--error': shown('headcount') }">
											<span id="mp-hc" class="g-form-row__label">{{ __("People needed") }}</span>
											<span
												class="flex items-center justify-end gap-3"
												role="group"
												aria-labelledby="mp-hc"
											>
												<GIconButton
													:label="__('One fewer')"
													:disabled="model.headcount <= 1"
													@click="model.headcount--"
												>
													<Minus class="h-5 w-5" aria-hidden="true" />
												</GIconButton>
												<output class="min-w-6 text-center" aria-live="polite">{{
													model.headcount
												}}</output>
												<GIconButton
													:label="__('One more')"
													:disabled="model.headcount >= MAX_HEADCOUNT"
													@click="model.headcount++"
												>
													<Plus class="h-5 w-5" aria-hidden="true" />
												</GIconButton>
											</span>
										</div>
										<FormField
											fieldtype="Link"
											options="Department"
											:label="__('Department')"
											reqd
											:placeholder="__('Choose…')"
											v-model="model.department"
											:display="departmentLabel(model.department)"
											:error-message="shown('department')"
										/>
										<FormField
											fieldtype="Select"
											:label="__('Location')"
											reqd
											:placeholder="__('Choose…')"
											:document-list="siteOptions"
											v-model="model.locationChoice"
											:error-message="shown('locationChoice')"
										/>
										<FormField
											v-if="model.locationChoice === OTHER_SITE"
											fieldtype="Small Text"
											:label="__('Where will they work?')"
											reqd
											:placeholder="__('Place, and why')"
											v-model="model.location_other"
											:error-message="shown('location_other')"
										/>
										<!-- locked: the sender is the hiring manager -->
										<div class="g-form-row g-form-row--readonly">
											<span class="g-form-row__label">{{ __("Reports to") }}</span>
											<span class="g-form-row__value">{{ __("You") }}</span>
											<Lock class="h-4 w-4 flex-none" aria-hidden="true" />
										</div>
									</div>
								</section>

								<!-- 2 Type -->
								<template v-else-if="step === 1">
									<section class="g-form-section">
										<h3 id="mp-etype" class="g-eyebrow">{{ __("Employment type") }}</h3>
										<GListPanel
											role="radiogroup"
											aria-labelledby="mp-etype"
											@keydown="
												radioKey(
													$event,
													etypeValues,
													model.employment_type,
													(v) => (model.employment_type = v)
												)
											"
										>
											<GListRow
												v-for="type in EMPLOYMENT_TYPES"
												:key="type.value"
												role="radio"
												:aria-checked="model.employment_type === type.value"
												:tabindex="tabStop(model.employment_type, type.value, etypeValues)"
												:label="__(type.label)"
												:sublabel="__(type.hint)"
												:chevron="false"
												@click="model.employment_type = type.value"
											>
												<template #badge
													><Check
														v-if="model.employment_type === type.value"
														class="h-5 w-5 flex-none"
														aria-hidden="true"
												/></template>
											</GListRow>
										</GListPanel>
										<p v-if="shown('employment_type')" class="g-field-error" role="alert">
											{{ shown("employment_type") }}
										</p>
									</section>
									<section class="g-form-section">
										<h3 id="mp-kind" class="g-eyebrow">{{ __("What is this for?") }}</h3>
										<GListPanel
											role="radiogroup"
											aria-labelledby="mp-kind"
											@keydown="
												radioKey(
													$event,
													kindValues,
													model.request_type,
													(v) => (model.request_type = v)
												)
											"
										>
											<GListRow
												v-for="type in REQUEST_TYPES"
												:key="type.value"
												role="radio"
												:aria-checked="model.request_type === type.value"
												:tabindex="tabStop(model.request_type, type.value, kindValues)"
												:label="__(type.label)"
												:chevron="false"
												@click="model.request_type = type.value"
											>
												<template #badge
													><Check
														v-if="model.request_type === type.value"
														class="h-5 w-5 flex-none"
														aria-hidden="true"
												/></template>
											</GListRow>
										</GListPanel>
									</section>
									<section v-if="model.request_type === 'Replacement'" class="g-form-section">
										<h3 id="mp-staff" class="g-eyebrow">{{ __("Who is being replaced?") }}</h3>
										<GSearchBar
											v-if="(staff.data?.length || 0) > 8"
											v-model="staffQuery"
											:placeholder="__('Search by name')"
											:label="__('Search by name')"
										/>
										<GListPanel
											v-if="staff.data?.length"
											role="radiogroup"
											aria-labelledby="mp-staff"
											@keydown="
												radioKey($event, staffValues, model.replacing_employee, pickStaffByName)
											"
										>
											<GListRow
												v-for="person in shownStaff"
												:key="person.name"
												role="radio"
												:aria-checked="model.replacing_employee === person.name"
												:tabindex="tabStop(model.replacing_employee, person.name, staffValues)"
												:label="person.employee_name"
												:sublabel="
													[person.designation, leftText(person)].filter(Boolean).join(' · ')
												"
												:chevron="false"
												@click="pickStaff(person)"
											>
												<template #badge
													><Check
														v-if="model.replacing_employee === person.name"
														class="h-5 w-5 flex-none"
														aria-hidden="true"
												/></template>
											</GListRow>
										</GListPanel>
										<ResourceError :resource="staff" :what="__('the staff list')" />
										<GEmptyState
											v-if="staff.fetched && !staff.error && !staff.data?.length"
											:title="__('No one in this department to replace')"
											:body="__('Choose New job above if this is not a replacement.')"
										/>
										<p class="g-form-footer">
											{{
												__("People in {0}. Anyone who left in the last 6 months is shown too.", [
													departmentLabel(model.department) || __("your department"),
												])
											}}
										</p>
										<p v-if="shown('replacing_employee')" class="g-field-error" role="alert">
											{{ shown("replacing_employee") }}
										</p>
									</section>
								</template>

								<!-- 3 Why -->
								<template v-else-if="step === 2">
									<section class="g-form-section">
										<h3 id="mp-soon" class="g-eyebrow">{{ __("How soon do you need them?") }}</h3>
										<GListPanel
											role="radiogroup"
											aria-labelledby="mp-soon"
											@keydown="
												radioKey($event, soonKeys, model.how_soon, (v) => (model.how_soon = v))
											"
										>
											<GListRow
												v-for="key in soonKeys"
												:key="key"
												role="radio"
												:aria-checked="model.how_soon === key"
												:tabindex="tabStop(model.how_soon, key, soonKeys)"
												:label="__(SOON_LABELS[key])"
												:chevron="false"
												@click="model.how_soon = key"
											>
												<template #badge
													><Check
														v-if="model.how_soon === key"
														class="h-5 w-5 flex-none"
														aria-hidden="true"
												/></template>
											</GListRow>
										</GListPanel>
										<p v-if="urgency" class="g-form-footer" role="status">
											<GStatusChip status="neutral" :label="__('{0} urgency', [__(urgency)])" />
										</p>
										<p v-if="shown('how_soon')" class="g-field-error" role="alert">
											{{ shown("how_soon") }}
										</p>
									</section>
									<section class="g-form-section">
										<div class="g-form-group">
											<FormField
												fieldtype="Small Text"
												:label="__('Why do you need this hire?')"
												reqd
												:placeholder="__('Type here')"
												v-model="model.justification"
												:error-message="shown('justification')"
											/>
											<FormField
												fieldtype="Date"
												:placeholder="__('Not fixed')"
												:label="__('Start date, if fixed') + ' (' + __('optional') + ')'"
												:min-date="tomorrow"
												v-model="model.start_date"
												:error-message="shown('start_date')"
											/>
										</div>
									</section>
								</template>

								<!-- 4 Pay -->
								<template v-else-if="step === 3">
									<section class="g-form-section">
										<h3 id="mp-band" class="g-eyebrow">{{ __("Pay band") }}</h3>
										<GListPanel
											role="radiogroup"
											aria-labelledby="mp-band"
											@keydown="radioKey($event, bandValues, model.band, (v) => (model.band = v))"
										>
											<GListRow
												v-for="b in BANDS"
												:key="b.value"
												role="radio"
												:aria-checked="model.band === b.value"
												:tabindex="tabStop(model.band, b.value, bandValues)"
												:label="b.label"
												:sublabel="__(b.meaning)"
												:chevron="false"
												@click="model.band = b.value"
											>
												<template #badge
													><Check
														v-if="model.band === b.value"
														class="h-5 w-5 flex-none"
														aria-hidden="true"
												/></template>
											</GListRow>
										</GListPanel>
										<p v-if="shown('band')" class="g-field-error" role="alert">
											{{ shown("band") }}
										</p>
									</section>
									<section class="g-form-section">
										<div class="g-form-group">
											<FormField
												fieldtype="Data"
												inputmode="decimal"
												:label="__('Budgeted salary a month')"
												reqd
												:placeholder="__('RM')"
												:model-value="moneyShown('budgeted_salary')"
												@focusin="startMoney('budgeted_salary')"
												@focusout="moneyFocus = ''"
												@update:model-value="typeMoney('budgeted_salary', $event)"
												:error-message="shown('budgeted_salary')"
											/>
											<FormField
												fieldtype="Data"
												inputmode="decimal"
												:label="__('Proposed salary a month')"
												reqd
												:placeholder="__('RM')"
												:model-value="moneyShown('proposed_salary')"
												@focusin="startMoney('proposed_salary')"
												@focusout="moneyFocus = ''"
												@update:model-value="typeMoney('proposed_salary', $event)"
												:error-message="shown('proposed_salary')"
											/>
										</div>
										<GBanner v-if="overBudget" variant="warning" class="mt-3">
											{{ __("Proposed is more than the budget. HR will see this.") }}
										</GBanner>
									</section>
								</template>

								<!-- 6 Review -->
								<template v-else-if="step === REVIEW_STEP">
									<section v-for="group in groups" :key="group.step" class="g-form-section">
										<div class="flex items-center justify-between">
											<h3 class="g-eyebrow">{{ group.title }}</h3>
											<button
												type="button"
												class="g-seclink g-focusable"
												@click="goTo(group.step)"
											>
												{{ __("Edit") }}<span class="sr-only"> {{ group.title }}</span
												><ChevronRight class="inline h-4 w-4" aria-hidden="true" />
											</button>
										</div>
										<div class="g-form-group">
											<div
												v-for="row in group.rows"
												:key="row.label"
												class="g-form-row g-form-row--readonly"
											>
												<span class="g-form-row__label">{{ row.label }}</span>
												<span class="g-form-row__value" :class="{ 'text-ink-600': !row.value }">{{
													row.value || __("Optional, left blank")
												}}</span>
											</div>
										</div>
									</section>
									<p class="g-form-footer">
										{{
											__(
												"After you send: your approver decides, then HR takes over. Follow it in Requests."
											)
										}}
									</p>
								</template>

								<!-- HR's questions for this step (step 5 is all of them), after the fixed fields -->
								<section v-if="step < REVIEW_STEP && shownQuestions.length" class="g-form-section">
									<template v-for="q in shownQuestions" :key="questionKey(q)">
										<div class="g-form-group">
											<FormField
												v-bind="questionField(q)"
												:label="q.required ? q.question : q.question + ' (' + __('optional') + ')'"
												:placeholder="
													['Choice', 'Yes-No'].includes(q.answer_type)
														? __('Choose…')
														: __('Type here')
												"
												:reqd="Boolean(q.required)"
												v-model="extra[questionKey(q)]"
												:error-message="shown(questionKey(q))"
											/>
										</div>
										<!-- optional files go with the draft job description (owner, 29 Oct 2026) -->
										<JobFilesRow
											class="mt-2 mb-2"
											v-if="isJobDescription(q)"
											v-model:files="model.job_files"
											v-model:uploading="filesUploading"
										/>
									</template>
								</section>
								<ResourceError :resource="questions" :what="__('the questions')" />
							</div>
						</div>

						<!-- pinned at the bottom, in thumb reach -->
						<div
							class="px-4 pt-4 pb-4 standalone:pb-safe-bottom bg-ground sticky bottom-0 w-full z-40 border-t border-divider"
						>
							<p v-if="sendError" class="g-field-error mb-2" role="alert">{{ sendError }}</p>
							<p v-if="blocker" id="mp-reason" class="g-form-footer mb-2" role="status">
								{{ blocker }}
								<button
									v-if="step === REVIEW_STEP && unfinished"
									type="button"
									class="g-backlink g-touch-area g-focusable"
									@click="goTo(unfinished.step)"
								>
									{{ __("Fix it") }}
								</button>
							</p>
							<div class="flex items-center gap-3">
								<GGhostButton :label="step === 0 ? __('Cancel') : __('Back')" @click="back" />
								<GButton
									class="grow"
									:class="{ 'g-btn--disabled': blocker }"
									:label="step === REVIEW_STEP ? __('Send') : __('Next')"
									:pending-label="__('Sending…')"
									:pending="sending"
									:aria-disabled="blocker ? 'true' : undefined"
									:aria-describedby="blocker ? 'mp-reason' : undefined"
									@click="next"
								/>
							</div>
						</div>
					</div>
				</div>
			</div>

			<GActionSheet
				:is-open="leaveOpen"
				:title="__('Keep as draft?')"
				:actions="leaveActions"
				@select="onLeave"
				@did-dismiss="leaveOpen = false"
			>
				<p class="g-form-footer text-center">
					{{ __("Your answers are saved on this phone. Finish it later from Requests.") }}
				</p>
			</GActionSheet>
		</ion-content>
	</GPage>
</template>

<script setup>
import { IonContent } from "@ionic/vue"
import { Check, ChevronRight, Lock, Minus, Plus, Users } from "lucide-vue-next"
import { createResource } from "frappe-ui"
import JobFilesRow from "@/components/JobFilesRow.vue"
import { computed, inject, nextTick, reactive, ref, watch } from "vue"
import { useRouter } from "vue-router"

import FormField from "@/components/FormField.vue"
import ResourceError from "@/components/ResourceError.vue"
import ShellHeader from "@/components/ShellHeader.vue"
import GBanner from "@/components/glass/GBanner.vue"
import GActionSheet from "@/components/glass/GActionSheet.vue"
import GButton from "@/components/glass/GButton.vue"
import GEmptyState from "@/components/glass/GEmptyState.vue"
import GGhostButton from "@/components/glass/GGhostButton.vue"
import GIconButton from "@/components/glass/GIconButton.vue"
import GListPanel from "@/components/glass/GListPanel.vue"
import GListRow from "@/components/glass/GListRow.vue"
import GPage from "@/components/glass/GPage.vue"
import GSearchBar from "@/components/glass/GSearchBar.vue"
import GStatusChip from "@/components/glass/GStatusChip.vue"
import { gToast } from "@/components/glass/toast"
import { reloadRequestLists } from "@/data/requestLists"
import { departmentLabel } from "@/utils/departmentLabel"
import { saveFailedSentence } from "@/utils/loudRequest"
import { goBackOrHome } from "@/utils/navigation"
import { sessionUser } from "@/utils/personalCache"
import {
	BANDS,
	EMPLOYMENT_TYPES,
	MAX_HEADCOUNT,
	OTHER_SITE,
	REQUEST_TYPES,
	REVIEW_STEP,
	SOON_LABELS,
	STEPS,
	URGENCY_BY_HOW_SOON,
	blankModel,
	buildInsertPayload,
	clearDraft,
	isJobDescription,
	nextBlock,
	questionField,
	questionKey,
	moneyText,
	parseMoney,
	rovingNext,
	tabStop,
	readDraft,
	visibleQuestions,
	reviewGroups,
	stepProblems,
	writeDraft,
} from "@/utils/manpowerRequest"
import dayjs from "dayjs"

const __ = inject("$translate")
const employee = inject("$employee")
const router = useRouter()
const user = sessionUser()

const model = reactive(blankModel({ department: employee.data?.department || "" }))
const extra = reactive({})
const step = ref(0)
const furthest = ref(0)
const tried = reactive({})
const sending = ref(false)
// a file still uploading holds Next and Send, so it is never sent without it
const filesUploading = ref(false)
const sendError = ref("")
const leaveOpen = ref(false)
const scroller = ref(null)

// A draft left on this phone comes back where it was left.
const draft = readDraft(user)
if (draft?.model) {
	Object.assign(model, draft.model)
	Object.assign(extra, draft.extra || {})
	step.value = furthest.value = Math.min(Number(draft.step) || 0, REVIEW_STEP)
	console.info("[manpower] draft restored at step", step.value + 1)
}
// the sender's department arrives with the employee on a cold start
watch(
	() => employee.data?.department,
	(department) => {
		if (department && !model.department) model.department = department
	}
)

const canRequest = createResource({ url: "hrms.api.manpower.can_request", auto: true })
// Fail closed, but not while it is still asking: a spinner-free page that flashes "no" is worse.
const cannotRequest = computed(() => canRequest.fetched && canRequest.data !== true)

const questions = createResource({ url: "hrms.api.manpower.get_questions", auto: true })
const allQuestions = computed(() => questions.data || [])
const stepQuestions = computed(() =>
	allQuestions.value.filter((q) => Number(q.step) === step.value + 1)
)

const sites = createResource({
	url: "frappe.client.get_list",
	params: {
		doctype: "Shift Location",
		fields: ["name"],
		order_by: "name asc",
		limit_page_length: 100,
	},
	auto: true,
})
const siteOptions = computed(() => [
	...(sites.data || []).map((site) => ({ label: site.name, value: site.name })),
	{ label: __("Other"), value: OTHER_SITE },
])
const soonKeys = Object.keys(URGENCY_BY_HOW_SOON)
const shownQuestions = computed(() => visibleQuestions(stepQuestions.value, extra))
const staff = createResource({
	url: "hrms.api.manpower.replaceable_staff",
	makeParams: () => ({ department: model.department }),
})
const staffQuery = ref("")
const shownStaff = computed(() => {
	const q = staffQuery.value.trim().toLowerCase()
	// the chosen person stays in the list whatever the search says
	return (staff.data || []).filter(
		(p) => !q || p.employee_name.toLowerCase().includes(q) || p.name === model.replacing_employee
	)
})
const staffValues = computed(() => shownStaff.value.map((p) => p.name))
const etypeValues = EMPLOYMENT_TYPES.map((e) => e.value)
const kindValues = REQUEST_TYPES.map((r) => r.value)
const bandValues = BANDS.map((b) => b.value)
const urgency = computed(() => URGENCY_BY_HOW_SOON[model.how_soon])
const tomorrow = dayjs().add(1, "day").format("YYYY-MM-DD")
const overBudget = computed(
	() =>
		Number(model.proposed_salary) > Number(model.budgeted_salary) &&
		Number(model.budgeted_salary) > 0
)
watch(
	() => [step.value, model.request_type, model.department],
	([at, type, department]) => {
		if (at === 1 && type === "Replacement" && department) staff.reload()
	},
	{ immediate: true }
)
// a department change makes the earlier pick wrong (the server needs the same department)
watch(
	() => model.department,
	() => {
		Object.assign(model, { replacing_employee: "", replacing_label: "" })
		staffQuery.value = ""
	}
)

// Money: while the field is focused it shows what was typed ("2500.", "2500.0"); it formats on blur.
const moneyFocus = ref("")
const moneyRaw = ref("")
const moneyShown = (field) =>
	moneyFocus.value === field ? moneyRaw.value : moneyText(model[field])
function startMoney(field) {
	if (moneyFocus.value === field) return
	moneyFocus.value = field
	moneyRaw.value = String(model[field] ?? "")
}
function typeMoney(field, text) {
	moneyRaw.value = text
	model[field] = parseMoney(text)
}

// Radio rows: arrows move the choice and the focus; only the chosen row is a tab stop.
function radioKey(event, values, chosen, pick) {
	const to = rovingNext(event.key, values.indexOf(chosen), values.length)
	if (to < 0) return
	event.preventDefault()
	pick(values[to])
	nextTick(() => event.currentTarget.querySelectorAll('[role="radio"]')[to]?.focus())
}
// "Left 12 Sep" for a leaver, in the person's language; nothing for staff still here
const leftText = (person) =>
	person.status === "Active"
		? ""
		: person.relieving_date
		? __("Left {0}", [dayjs(person.relieving_date).format("D MMM")])
		: __("Left")
const pickStaffByName = (name) => pickStaff(staff.data.find((p) => p.name === name))
function pickStaff(person) {
	model.replacing_employee = person.name
	model.replacing_label = person.employee_name
}

const today = () => dayjs().format("YYYY-MM-DD")
const problems = computed(() =>
	stepProblems(step.value, model, extra, allQuestions.value, { today: today() })
)
const unfinished = computed(() => nextBlock(model, extra, allQuestions.value, { today: today() }))
// An error under a field only once the person has tried to go on from this step.
const shown = (field) =>
	tried[step.value]
		? problems.value.find((p) => p.field === field)?.message &&
		  __(problems.value.find((p) => p.field === field).message)
		: ""

// THE one place that lists every reason Next/Send is dimmed.
const blocker = computed(() => {
	if (sending.value) return ""
	if (filesUploading.value) return __("Wait for the file to finish uploading.")
	if (questions.loading && !questions.data) return __("Loading the questions…")
	if (questions.error) return __("The questions did not load. Try again.")
	if (step.value === REVIEW_STEP)
		return unfinished.value
			? __("Step {0} is not finished: {1}.", [
					unfinished.value.step + 1,
					__(unfinished.value.message),
			  ])
			: ""
	return problems.value[0] ? __(problems.value[0].message) : ""
})

const groups = computed(() =>
	step.value === REVIEW_STEP
		? reviewGroups(model, extra, allQuestions.value, {
				t: __,
				me: employee.data?.employee_name || __("You"),
		  })
		: []
)

function goTo(i) {
	step.value = i
	furthest.value = Math.max(furthest.value, i)
	nextTick(() => scroller.value && (scroller.value.scrollTop = 0))
}
function back() {
	if (step.value === 0) askToLeave()
	else goTo(step.value - 1)
}

const insert = createResource({ url: "frappe.client.insert" })
async function next() {
	if (sending.value) return
	// Dimmed, not dead: the tap shows what is missing under each field, and nothing else happens.
	if (blocker.value) {
		tried[step.value] = true
		if (step.value === REVIEW_STEP && unfinished.value) tried[unfinished.value.step] = true
		return
	}
	if (step.value < REVIEW_STEP) return goTo(step.value + 1)
	sending.value = true
	sendError.value = ""
	try {
		// ALWAYS the session employee: create permission is checked before the server fills it in
		const doc = buildInsertPayload(model, extra, allQuestions.value, employee.data?.name)
		const saved = await insert.submit({ doc })
		clearDraft(user)
		reloadRequestLists("manpower sent")
		gToast({ title: __("Sent"), text: __("Your manpower request was sent."), variant: "success" })
		router.replace({ name: "ManpowerRequestDetailView", params: { id: saved.name } })
	} catch (error) {
		// answers stay; the server's sentence is shown in place
		console.warn("[manpower] send failed", error?.message)
		sendError.value = saveFailedSentence(error, __("Could not send this request."))
	} finally {
		sending.value = false
	}
}

// ---- leaving part-way
const touched = computed(() =>
	Boolean(
		model.position_title ||
			model.justification ||
			model.band ||
			Object.keys(extra).length ||
			step.value > 0
	)
)
const leaveActions = [
	{ key: "keep", label: __("Keep as draft") },
	{ key: "discard", label: __("Discard"), destructive: true },
]
function askToLeave() {
	if (!touched.value || cannotRequest.value) return goBackOrHome(router)
	leaveOpen.value = true
}
function onLeave(key) {
	leaveOpen.value = false
	if (key === "keep") {
		writeDraft(user, { step: step.value, model: { ...model }, extra: { ...extra } })
		gToast({ title: __("Saved as a draft"), variant: "success" })
	} else clearDraft(user)
	goBackOrHome(router)
}
</script>

<style scoped>
.mp-track {
	height: 4px;
	margin-top: 8px;
	border-radius: 2px;
	background: var(--g-track-solid);
	overflow: hidden;
}
.mp-fill {
	height: 100%;
	background: var(--g-accent-ink);
	transform-origin: left;
	transition: transform var(--g-motion-progress-duration) var(--g-motion-progress-easing);
}
@media (prefers-reduced-motion: reduce) {
	.mp-fill {
		transition: none;
	}
}
</style>
