<template>
	<div class="flex flex-col h-full w-full form-view-root" v-if="isFormReady">
		<!-- No bg-ground here (8.4): this container is full-bleed over the page,
	     and an opaque page-colour fill painted straight over the light field,
	     so every form and detail screen rendered flat. The sticky header and
	     footer below KEEP their fill — they need to be opaque as content
	     scrolls under them. -->
		<div class="w-full h-full flex flex-col">
			<!-- The one header (alpha.5). It was a hand-drawn bar with a 2px
			     hairline at lg:, a phone-only Back and a second desktop-only
			     "Back" link inside the form. Back is one control now, at every
			     width, and it still asks before discarding typed work. -->
			<ShellHeader bare :title="__(formTitle(props.doctype, !id))" :back="confirmBack">
				<template v-if="id" #actions>
					<!-- No id badge (ruling L4: ids never reach users; alpha.5 walk found
					     "HR-LAP-2026-00043" on every open request). -->
					<!-- GStatusChip, not frappe-ui Badge (8.9). The same value rendered
					     as a FILLED amber "Open" pill here and an OUTLINED uppercase
					     "OPEN" on the list — two chip designs for one status, because
					     the detail header used a different component from every list.
					     GStatusChip owns the 16-state -> 6-variant map; there is no
					     second answer now. -->
					<GStatusChip
						v-if="status"
						:status="status"
						:label="__(status, null, doctype)"
						class="whitespace-nowrap"
					/>

					<Dropdown
						class="ml-auto"
						:options="[
							{
								label: __('Delete'),
								condition: showDeleteButton,
								onClick: () => (showDeleteDialog = true),
							},
							{ label: __('Reload'), onClick: () => reloadDoc() },
							{
								label: __('Download PDF'),
								condition: () => props.showDownloadPDFButton,
								onClick: () => handleDownload(),
							},
						]"
						:button="{
							label: __('Menu'),
							icon: 'more-horizontal',
							variant: 'ghost',
						}"
					/>
				</template>
			</ShellHeader>

			<!-- Form. Focusable so a keyboard user can scroll it (WCAG 2.1.1;
			     axe scrollable-region-focusable, alpha.5 served gate). -->
			<div
				class="grow overflow-y-auto"
				tabindex="0"
				:aria-label="__(formTitle(props.doctype, !id))"
			>
				<!-- The one content column (§20.3): 720px, left-aligned against the
				     side nav at lg:. It was sm:max-w-2xl (672px) centred. -->
				<div class="w-full max-w-content-column-lg mx-auto lg:mx-0">
					<slot name="beforeFields"></slot>
					<!-- Tabs -->
					<template v-if="tabbedView">
						<!-- One tab is no choice: its button does nothing and the strip only
						     spends a sticky row (the expense claim's lone "Expenses"). -->
						<div
							v-if="tabs?.length > 1"
							class="px-4 sticky top-0 z-overlay bg-ground text-sm font-medium text-center text-ink-600 border-b border-divider"
						>
							<ul class="flex -mb-px overflow-auto hide-scrollbar">
								<li class="mr-2 whitespace-nowrap" v-for="tab in tabs" :key="tab.name">
									<button
										@click="activeTab = tab.name"
										class="inline-block py-4 px-2 border-b-2 border-transparent"
										:class="[
											activeTab === tab.name
												? '!text-accent-ink !border-accent-ink !font-bold'
												: 'hover:text-inkbase hover:border-divider',
										]"
									>
										{{ __(tab.name, null, props.doctype) }}
									</button>
								</li>
							</ul>
						</div>

						<template v-for="(fieldList, tabName, index) in tabFields" :key="tabName">
							<div
								v-show="tabName === activeTab"
								class="g-form-body"
								@focusin="touchForm"
								@click.capture="touchForm"
							>
								<!-- Each section is ONE inset group (alpha.6 B2, Apple HIG Lists and
								     tables): a small grey heading, then the rows on one rounded surface. -->
								<section
									v-for="group in groupFields(fieldList, rowShown)"
									:key="group.key"
									class="g-form-section"
								>
									<h2 v-if="group.label" class="g-form-section__title">
										{{ sentenceCase(__(plainLabel(group.label), null, props.doctype)) }}
									</h2>
									<template v-for="(segment, s) in group.segments" :key="s">
										<div v-if="segment.kind === 'rows'" class="g-form-group">
											<FormField
												v-for="field in segment.fields"
												:key="field.fieldname"
												:fieldtype="field.fieldtype"
												:fieldname="field.fieldname"
												v-model="formModel[field.fieldname]"
												:default="field.default"
												:label="__(field.label, null, props.doctype)"
												:options="field.options"
												:linkFilters="field.linkFilters"
												:documentList="field.documentList"
												:readOnly="isFieldReadOnly(field)"
												:reqd="Boolean(field.reqd)"
												:hidden="Boolean(field.hidden)"
												:errorMessage="field.error_message"
												:minDate="field.minDate"
												:maxDate="field.maxDate"
											/>
										</div>
										<slot
											v-else
											:name="segment.field.fieldname"
											:isFormReadOnly="isFormReadOnly"
										></slot>
									</template>
								</section>

								<!-- Attachment upload -->
								<div
									class="flex flex-row gap-2 items-center justify-center p-5"
									v-if="isFileUploading"
								>
									<GSkeleton width="12px" height="12px" radius="var(--g-radius-well)" />
									<span class="text-inkbase text-sm">{{ __("Uploading...") }} </span>
								</div>

								<FileUploaderView
									v-else-if="showAttachmentView && index === 0"
									v-model="fileAttachments"
									@handleFileSelect="handleFileSelect"
									@handleFileDelete="handleFileDelete"
								/>
							</div>
						</template>
					</template>

					<div class="g-form-body" v-else @focusin="touchForm" @click.capture="touchForm">
						<!-- Each section is ONE inset group (alpha.6 B2, Apple HIG Lists and
						     tables): a small grey heading, then the rows on one rounded surface. -->
						<section
							v-for="group in groupFields(shownFields, rowShown)"
							:key="group.key"
							class="g-form-section"
						>
							<h2 v-if="group.label" class="g-form-section__title">
								{{ sentenceCase(__(plainLabel(group.label), null, props.doctype)) }}
							</h2>
							<template v-for="(segment, s) in group.segments" :key="s">
								<div v-if="segment.kind === 'rows'" class="g-form-group">
									<FormField
										v-for="field in segment.fields"
										:key="field.fieldname"
										:fieldtype="field.fieldtype"
										:fieldname="field.fieldname"
										v-model="formModel[field.fieldname]"
										:default="field.default"
										:label="__(field.label, null, props.doctype)"
										:options="field.options"
										:linkFilters="field.linkFilters"
										:documentList="field.documentList"
										:readOnly="isFieldReadOnly(field)"
										:reqd="Boolean(field.reqd)"
										:hidden="Boolean(field.hidden)"
										:errorMessage="field.error_message"
										:minDate="field.minDate"
										:maxDate="field.maxDate"
									/>
								</div>
								<slot
									v-else
									:name="segment.field.fieldname"
									:isFormReadOnly="isFormReadOnly"
								></slot>
							</template>
						</section>

						<!-- Attachment upload -->
						<div
							class="flex flex-row gap-2 items-center justify-center p-5"
							v-if="isFileUploading"
						>
							<GSkeleton width="12px" height="12px" radius="var(--g-radius-well)" />
							<span class="text-inkbase text-sm">{{ __("Uploading...") }} </span>
						</div>

						<FileUploaderView
							v-else-if="showAttachmentView"
							v-model="fileAttachments"
							@handleFileSelect="handleFileSelect"
							@handleFileDelete="handleFileDelete"
						/>
					</div>
				</div>
			</div>

			<!-- Form Primary/Secondary Button -->
			<!-- custom form button eg: Download button in salary slips -->
			<div
				v-if="!showFormButton"
				class="px-4 pt-4 pb-4 standalone:pb-safe-bottom bg-ground sticky bottom-0 w-full z-40 border-t border-divider"
			>
				<div class="w-full max-w-content-column-lg mx-auto lg:mx-0">
					<slot name="formButton"></slot>
				</div>
			</div>

			<!-- workflow actions -->
			<WorkflowActionSheet
				v-else-if="!isFormDirty && workflow?.hasWorkflow"
				:doc="documentResource.doc"
				:workflow="workflow"
				@workflowApplied="reloadDoc()"
			/>

			<!-- approver: the decision lives in RequestActionSheet (Home > Team
			     Requests). A request opened from a notification landed here, on the
			     applicant's edit form, with no Approve or Reject anywhere — the
			     approver could only edit fields. Open the same sheet from here. -->
			<div
				v-else-if="canReview"
				class="px-4 pt-4 pb-4 standalone:pb-safe-bottom bg-ground sticky bottom-0 w-full z-40 border-t border-divider"
			>
				<div class="w-full max-w-content-column-lg mx-auto lg:mx-0">
					<GButton :label="__('Review request')" @click="openReviewSheet" />
				</div>
			</div>

			<!-- save/submit/cancel -->
			<div
				v-else-if="isFormDirty || (!workflow?.hasWorkflow && formButton)"
				class="px-4 pt-4 pb-4 standalone:pb-safe-bottom bg-ground sticky bottom-0 w-full z-40 border-t border-divider"
			>
				<div class="w-full max-w-content-column-lg mx-auto lg:mx-0">
					<ErrorMessage
						class="mb-2"
						:message="
							formErrorMessage ||
							docList?.insert?.error ||
							documentResource?.setValue?.error ||
							finalize.error
						"
					/>

					<!-- GButton, not a frappe-ui Button painted with utilities (8.17).
				     This was the ONLY primary action in the product that bypassed
				     the primary component, which is precisely why it was the only
				     one that drifted: it wrote `!bg-accent` expecting the brand and
				     got --accent-ink, dark olive on light. GButton resolves
				     --g-brand directly, so it cannot. -->
					<GButton
						:label="formButton === 'Save' ? __(saveLabel) : __(formButton)"
						:pending-label="saveLabel.startsWith('Send') ? __('Sending…') : __('Saving…')"
						:pending="
							docList.insert.loading || documentResource?.setValue?.loading || finalize.loading
						"
						:disabled="formButton === 'Save' && Boolean(saveError)"
						:class="formButton === 'Cancel' ? 'g-confirm__destructive' : undefined"
						@click="formButton === 'Save' ? saveForm() : submitOrCancelForm()"
					/>
				</div>
			</div>
		</div>
	</div>

	<!-- v-else: the whole form UI above — including the header and its Back
	     button — renders only once the document has loaded. Without this branch
	     a slow or failed fetch (404, no permission, dropped network) left a
	     blank screen with no spinner, no error and no way back. Loading shows an
	     inline indicator; a failed load shows the reason with Back + Try again,
	     so the user is never stranded on a detail/edit screen. Only reached for
	     an existing id (new forms are ready immediately, isFormReady). -->
	<div v-else class="flex flex-col h-full w-full form-view-root">
		<ShellHeader
			bare
			:title="__(formTitle(props.doctype, !id))"
			:back="() => goBackOrHome(router)"
		/>
		<div class="grow overflow-y-auto flex items-center justify-center p-6">
			<div
				v-if="documentResource.get.loading"
				class="flex flex-col items-center gap-3 text-ink-600"
			>
				<GSkeleton width="24px" height="24px" radius="var(--g-radius-well)" />
				<span class="text-caption">{{ __("Loading…") }}</span>
			</div>
			<GEmptyState
				v-else
				:title="__('Could not open this {0}', [__(props.noun)])"
				:body="
					__(
						'It may have been removed, or you may not have access. Check your connection and try again.'
					)
				"
			>
				<template #action>
					<GButton :label="__('Try again')" @click="reloadDoc()" />
				</template>
			</GEmptyState>
		</div>
	</div>

	<!-- Confirmation dialogs — GConfirm carries GModal's focus-trap workaround
	     (§16.3), which frappe-ui's Dialog does not. Same state variables, same
	     handlers: this is a presentation swap only. -->
	<!-- Approver's decision sheet — the same component the Team Requests list
	     opens, so approve/reject/submit stay one code path. Reload on close so
	     the form shows what the server did. -->
	<GModal :is-open="showReviewSheet" @did-dismiss="closeReviewSheet">
		<RequestActionSheet
			v-if="showReviewSheet && reviewRequest"
			:fields="REQUEST_SUMMARY_FIELDS[props.doctype]"
			:showOpenForm="false"
			v-model="reviewRequest"
		/>
	</GModal>

	<GConfirm
		:is-open="showDeleteDialog"
		:title="__('Delete {0}', [__(props.noun)])"
		:confirm-label="__('Delete')"
		:cancel-label="__('Cancel')"
		destructive
		@confirm="handleDocDelete"
		@cancel="showDeleteDialog = false"
	>
		{{ __("Are you sure you want to delete this {0}?", [__(props.noun)]) }}
	</GConfirm>

	<GConfirm
		:is-open="showSubmitDialog"
		:title="__('Confirm')"
		:confirm-label="__('Yes')"
		:cancel-label="__('No')"
		@confirm="handleDocUpdate('submit')"
		@cancel="showSubmitDialog = false"
	>
		{{ __("Send this {0} for approval?", [__(props.noun)]) }}
	</GConfirm>

	<GConfirm
		:is-open="showDiscardDialog"
		:title="__('Discard changes?')"
		:confirm-label="__('Discard')"
		:cancel-label="__('Keep editing')"
		destructive
		@confirm="discardAndLeave"
		@cancel="showDiscardDialog = false"
	>
		{{ __("You have unsaved changes. Leave without saving?") }}
	</GConfirm>

	<Dialog v-model="showCancelDialog">
		<template #body-title>
			<h2 class="text-xl font-bold">{{ __("Confirm") }}</h2>
		</template>
		<template #body-content>
			<p>
				{{ __("Cancel this {0}?", [__(props.noun)]) }}
			</p>
		</template>
		<template #actions>
			<div class="flex flex-row gap-4">
				<Button variant="outline" class="py-5 w-full" @click="showCancelDialog = false">
					{{ __("No") }}
				</Button>
				<Button variant="solid" @click="handleDocUpdate('cancel')" class="py-5 w-full">
					{{ __("Yes") }}
				</Button>
			</div>
		</template>
	</Dialog>
</template>

<script setup>
import ShellHeader from "@/components/ShellHeader.vue"
import { splitFieldsByTab } from "@/utils/formTabs"
import GButton from "@/components/glass/GButton.vue"
import GConfirm from "@/components/glass/GConfirm.vue"
import { computed, inject, nextTick, onMounted, ref, watch } from "vue"
import { useRouter } from "vue-router"
import GStatusChip from "@/components/glass/GStatusChip.vue"
import GEmptyState from "@/components/glass/GEmptyState.vue"

import { goBackOrHome } from "@/utils/navigation"
import {
	ErrorMessage,
	createListResource,
	createDocumentResource,
	toast,
	createResource,
	Dropdown,
	Dialog,
} from "frappe-ui"
import GSkeleton from "@/components/glass/GSkeleton.vue"
import FormField from "@/components/FormField.vue"
import { dropEmptySections, isShown } from "@/utils/visibleSections"
import { groupFields } from "@/utils/formGroups"
import { sentenceCase } from "@/utils/sentenceCase"
import { sendLabel } from "@/utils/sendLabel"
import { plainLabel } from "@/utils/plainLabel"
import FileUploaderView from "@/components/FileUploaderView.vue"
import WorkflowActionSheet from "@/components/WorkflowActionSheet.vue"
import RequestActionSheet from "@/components/RequestActionSheet.vue"
import GModal from "@/components/glass/GModal.vue"
import { REQUEST_SUMMARY_FIELDS } from "@/data/config/requestSummaryFields"

import { FileAttachment } from "@/composables"
import useWorkflow from "@/composables/workflow"
import useDecisionCapability from "@/composables/decisionCapability"
import useApprovedCancel from "@/composables/approvedCancel"
import { getCompanyCurrency } from "@/data/currencies"
import { canOfferCancel } from "@/utils/cancelRule"
import { requestStatus } from "@/utils/requestStatus"
import { formTitle } from "@/utils/formTitle"
import { firstMessage } from "@/utils/loudRequest"
import { formatCurrency } from "@/utils/formatters"
import { useDownloadPDF } from "@/utils/commonUtils"

const props = defineProps({
	saveError: { type: String, default: "" },
	doctype: {
		type: String,
		required: true,
	},
	// The word an EMPLOYEE would use for the thing on this screen — "leave
	// request", "expense claim", "punch". Every sentence the shell shows is
	// built from this, because `props.doctype` is a table name and the people
	// reading these dialogs have never seen one. `__(doctype)` did not save
	// it: the translation files carry UI strings, not doctype names, so the
	// lookup missed and the raw name fell through.
	//
	// The default is a sentence rather than a word so that a screen which
	// forgets reads "Delete this request", which is vague but true, instead of
	// "Delete Employee Checkin", which is precise and meaningless.
	noun: {
		type: String,
		default: "this request",
	},
	modelValue: {
		type: Object,
		required: true,
	},
	isSubmittable: {
		type: Boolean,
		required: false,
		default: false,
	},
	fields: {
		type: Array,
		required: true,
	},
	id: {
		type: String,
		required: false,
	},
	tabbedView: {
		type: Boolean,
		required: false,
		default: false,
	},
	tabs: {
		type: Array,
		required: false,
	},
	showAttachmentView: {
		type: Boolean,
		required: false,
		default: false,
	},
	requireAttachment: {
		type: Boolean,
		required: false,
		default: false,
	},
	showFormButton: {
		type: Boolean,
		required: false,
		default: true,
	},
	showDownloadPDFButton: {
		type: Boolean,
		required: false,
		default: false,
	},
})
const emit = defineEmits(["validateForm", "update:modelValue", "formReloaded"])
const router = useRouter()
const { downloadPDF } = useDownloadPDF()

const __ = inject("$translate")
const currentUser = inject("$user")
const currentEmployee = inject("$employee")

// HR or the approver may cancel an approved request; the employee may not
// (owner ruling, 14 Sep 2026 — see utils/cancelRule.js).
const cancelViewer = computed(() => ({
	user: currentUser?.data?.name,
	roles: currentUser?.data?.roles || [],
	employee: currentEmployee?.data?.name,
}))

let activeTab = ref(props.tabs?.[0].name)
let fileAttachments = ref([])
let formErrorMessage = ref("")
let isFormDirty = ref(false)

// Guard against losing typed work: when the form is dirty, Back opens a discard
// confirm instead of navigating away silently. (The error-recovery Back is not
// wired here — there is no form to lose there.)
const showDiscardDialog = ref(false)
function confirmBack() {
	if (isFormDirty.value) {
		showDiscardDialog.value = true
	} else {
		goBackOrHome(router)
	}
}
function discardAndLeave() {
	showDiscardDialog.value = false
	goBackOrHome(router)
}
let isFormUpdated = ref(false)
let showDeleteDialog = ref(false)
let showSubmitDialog = ref(false)
let showCancelDialog = ref(false)
let isFileUploading = ref(false)
let workflow = ref(null)

const formModel = computed({
	get() {
		return props.modelValue
	},
	set(newValue) {
		emit("update:modelValue", newValue)
	},
})

const status = computed(() => {
	if (!props.id) return ""

	if (workflow.value) {
		const stateField = workflow.value.getWorkflowStateField()
		if (stateField) return formModel.value[stateField]
	}

	return requestStatus(props.doctype, formModel.value).label
})

// A new form has no server copy to diff against, so `dirty` was never armed
// and Back threw typed items away without asking. Dirty for a new form means:
// it differs from what it held when the employee FIRST touched it. The
// baseline is taken at that touch (capture phase, before any child handler
// mutates the model), so FormField's mount defaults and the seeds a parent
// applies after mount — approver, currency, an empty items table — are
// absorbed rather than mistaken for the employee's work.
let newDocBaseline = null
const formTouched = ref(false)
function touchForm() {
	if (formTouched.value) return
	formTouched.value = true
	if (!props.id) newDocBaseline = editableSnapshot()
}
// FormField seeds "" / false on mount and parents seed [] for tables: every
// flavour of "nothing here" compares equal.
const isEmptyValue = (value) =>
	value == null || value === "" || value === false || (Array.isArray(value) && value.length === 0)
function editableSnapshot() {
	const snapshot = {}
	for (const field of props.fields) {
		if (field.hidden || field.read_only) continue
		const value = formModel.value[field.fieldname]
		snapshot[field.fieldname] = isEmptyValue(value) ? null : value
	}
	return JSON.stringify(snapshot)
}

watch(
	() => formModel.value,
	() => {
		if (!props.id) {
			if (newDocBaseline !== null) isFormDirty.value = editableSnapshot() !== newDocBaseline
			return
		}

		if (isFormReady.value && !isFormUpdated.value) {
			isFormDirty.value = true
		} else if (isFormUpdated.value) {
			isFormUpdated.value = false
		}
	},
	{ deep: true }
)

//: The fields as drawn: a section heading only when something under it shows.
const shownFields = computed(() =>
	dropEmptySections(props.fields, formModel.value, isFieldReadOnly)
)
const tabFields = computed(() => splitFieldsByTab(shownFields.value, props.tabs))
//: Whether a row draws, for the one-row-section rule (alpha.7 B13).
const rowShown = (field) => isShown(field, formModel.value, isFieldReadOnly)

const attachedFiles = createResource({
	url: "hrms.api.get_attachments",
	params: {
		dt: props.doctype,
		dn: props.id,
	},
	transform(data) {
		return data.map((file) => ({ ...file, uploaded: true }))
	},
	onSuccess(data) {
		fileAttachments.value = data
	},
})

const handleFileSelect = (e) => {
	if (props.id) {
		uploadAllAttachments(props.doctype, props.id, [...e.target.files])
	} else {
		fileAttachments.value.push(...e.target.files)
	}
}

const handleFileDelete = async (fileObj) => {
	if (fileObj.uploaded) {
		const fileAttachment = new FileAttachment(fileObj)
		await fileAttachment.delete()
		await attachedFiles.reload()
	} else {
		fileAttachments.value = fileAttachments.value.filter((file) => file.name !== fileObj.name)
	}
}

async function uploadAllAttachments(documentType, documentName, attachments) {
	isFileUploading.value = true

	const uploadPromises = attachments.map((attachment) => {
		const fileAttachment = new FileAttachment(attachment)
		return fileAttachment.upload(documentType, documentName, "").then((fileDoc) => {
			fileDoc.uploaded = true
			if (props.id) {
				fileAttachments.value.push(fileDoc)
			}
		})
	})

	await Promise.allSettled(uploadPromises)
	isFileUploading.value = false
}

// CRUD for doc
const docList = createListResource({
	doctype: props.doctype,
	insert: {
		async onSuccess(data) {
			toast({
				title: __("Success"),
				text: __("Your {0} was created.", [__(props.noun)]),
				icon: "check-circle",
				position: "bottom-center",
				iconClasses: "text-green-500",
			})
			await uploadAllAttachments(data.doctype, data.name, fileAttachments.value)

			router.replace({
				name: `${props.doctype.replace(/\s+/g, "")}DetailView`,
				params: { id: data.name },
			})
		},
		onError(error) {
			// The server names the refusal (balance, allocation period, approver,
			// holiday list). Dropping it left the employee with "unknown error".
			toast({
				title: __("Error"),
				text: __("Could not save this {0}. {1}", [__(props.noun), firstMessage(error)]),
				icon: "alert-circle",
				position: "bottom-center",
				iconClasses: "text-red-500",
			})
			console.log(`Error creating ${props.doctype}`, firstMessage(error))
		},
	},
})

const documentResource = createDocumentResource({
	doctype: props.doctype,
	name: props.id,
	setValue: {
		onSuccess() {
			toast({
				title: __("Success"),
				text: __("Your {0} was updated.", [__(props.noun)]),
				icon: "check-circle",
				position: "bottom-center",
				iconClasses: "text-green-500",
			})
		},
		onError(error) {
			toast({
				title: __("Error"),
				text: __("Could not save this {0}. {1}", [__(props.noun), firstMessage(error)]),
				icon: "alert-circle",
				position: "bottom-center",
				iconClasses: "text-red-500",
			})
			console.log(`Error updating ${props.doctype}`, firstMessage(error))
		},
	},
	delete: {
		onSuccess() {
			goBackOrHome(router)
			toast({
				title: __("Success"),
				text: __("Your {0} was deleted.", [__(props.noun)]),
				icon: "check-circle",
				position: "bottom-center",
				iconClasses: "text-green-500",
			})
		},
		onError(error) {
			toast({
				title: __("Error"),
				text: __("Could not save this {0}. {1}", [__(props.noun), firstMessage(error)]),
				icon: "alert-circle",
				position: "bottom-center",
				iconClasses: "text-red-500",
			})
			console.log(`Error deleting ${props.doctype}`, firstMessage(error))
		},
	},
})

// docstatus is a TRANSITION, not a field: frappe.client.set_value refuses it
// ("Cannot edit standard fields"), so Submit and Cancel sent through setValue
// failed silently. The server performs the transition — the same endpoint
// RequestActionSheet uses — and runs validate/on_submit/on_cancel with it.
const finalize = createResource({
	url: "hrms.api.approval.finalize",
	onSuccess() {
		toast({
			title: __("Success"),
			text: __("Your {0} was updated.", [__(props.noun)]),
			icon: "check-circle",
			position: "bottom-center",
			iconClasses: "text-green-500",
		})
	},
	onError(error) {
		console.warn(`[FormView] ${props.doctype} transition failed:`, error)
		toast({
			title: __("Error"),
			text: firstMessage(error, __("Could not save this {0}.", [__(props.noun)])),
			icon: "alert-circle",
			position: "bottom-center",
			iconClasses: "text-red-500",
		})
	},
})

const docPermissions = createResource({
	url: "frappe.client.get_doc_permissions",
	params: { doctype: props.doctype, docname: props.id },
})

const permittedWriteFields = createResource({
	url: "hrms.api.get_permitted_fields_for_write",
	params: { doctype: props.doctype },
})

// Approved: Cancel only when the server's guard says this viewer may.
const approvedCancel = useApprovedCancel(() =>
	props.id && canOfferCancel(formModel.value, props.doctype, cancelViewer.value) === "approved"
		? { doctype: props.doctype, name: props.id, modified: formModel.value?.modified }
		: null
)

//: What the Save button SAYS (owner ruling Q1): "Send to {name}" on a new
//: request. formButton stays the action key ("Save" still means save).
const saveLabel = computed(() =>
	sendLabel({ doctype: props.doctype, isNew: !props.id, fields: props.fields, model: formModel.value })
)

const formButton = computed(() => {
	if (!props.showFormButton) return null

	if (props.id && props.isSubmittable && !isFormDirty.value) {
		// Decision-bearing requests use the capability-backed review sheet,
		// including already-decided drafts. Native Submit alone is insufficient.
		if (
			formModel.value.docstatus === 0 &&
			hasPermission("submit") &&
			!REQUEST_SUMMARY_FIELDS[props.doctype]
		) {
			return "Submit"
		}
		const cancelOffer = canOfferCancel(formModel.value, props.doctype, cancelViewer.value)
		if (
			(cancelOffer === "approved" && approvedCancel.value) ||
			(cancelOffer === "own" && hasPermission("cancel"))
		) {
			return "Cancel"
		}
		// submitted-and-cancel-blocked, or any other docstatus: no button.
		return null
	} else if (formModel.value.docstatus !== 2) {
		return "Save"
	}
	return null
})

// Use the same document capability as the sheet and Desk. Field grants alone
// do not describe the server's routed-manager authority.
const decisionCapability = useDecisionCapability(
	() => documentResource,
	() => ({ doctype: props.doctype, name: props.id }),
	() =>
		toast({
			title: __("Request changed"),
			text: __("This request changed. Reload it before deciding."),
			icon: "alert-circle",
		})
)
const canReview = computed(() => {
	if (!props.id || isFormDirty.value || workflow.value?.hasWorkflow) return false
	return (
		Boolean(REQUEST_SUMMARY_FIELDS[props.doctype]) && decisionCapability.actions.value.length > 0
	)
})
const showReviewSheet = ref(false)
const reviewRequest = ref(null)
function openReviewSheet() {
	if (!canReview.value) return
	reviewRequest.value = { doctype: props.doctype, name: props.id }
	showReviewSheet.value = true
}
function closeReviewSheet() {
	showReviewSheet.value = false
	console.info("[FormView] review sheet closed, reloading", props.doctype, props.id)
	reloadDoc()
}

function showDeleteButton() {
	return props.id && formModel.value.docstatus !== 1 && hasPermission("delete")
}

function hasPermission(action) {
	return docPermissions.data?.permissions[action]
}

function isFieldReadOnly(field) {
	return (
		Boolean(field.read_only) ||
		isFormReadOnly.value ||
		(props.id && !permittedWriteFields.data?.includes(field.fieldname))
	)
}

function handleDocInsert() {
	if (!validateMandatoryFields()) return
	if (props.requireAttachment && !fileAttachments.value.length) {
		formErrorMessage.value = __("A supporting attachment is required")
		return
	}
	docList.insert.submit(formModel.value)
}

function validateMandatoryFields() {
	const errorFields = props.fields
		.filter((field) => {
			if (!field.reqd || field.hidden) return false
			const value = formModel.value[field.fieldname]
			// an empty child table ([]) is truthy — !value missed it, so a
			// required table (e.g. Expense Claim's expenses) submitted empty.
			return Array.isArray(value) ? value.length === 0 : !value
		})
		.map((field) => field.label)

	if (errorFields.length) {
		formErrorMessage.value = `${errorFields.join(", ")} ${
			errorFields.length > 1 ? "fields are mandatory" : "field is mandatory"
		}`
		return false
	}

	// A field showing an inline validation error (To Date before From Date,
	// claimed hours over the punch-verified cap, half-day steps) must block the
	// save. Without this the form submitted with the error visible, and the user
	// got a second, server-worded failure instead of the inline message stopping
	// them. error_message is the inline channel — set on invalid, "" on valid.
	const invalidField = props.fields.find((field) => !field.hidden && field.error_message)
	if (invalidField) {
		formErrorMessage.value = invalidField.error_message
		return false
	}

	formErrorMessage.value = ""
	return true
}

async function handleDocUpdate(action) {
	// Close the confirm dialog UP FRONT: the submit awaits the server, and the
	// GConfirm/Dialog "Yes" button has no pending state, so a second tap during
	// that window used to fire a duplicate submit/cancel.
	if (action === "submit") showSubmitDialog.value = false
	else if (action === "cancel") showCancelDialog.value = false

	if (!documentResource.doc) return
	if (!validateMandatoryFields()) return

	if (action === "submit" || action === "cancel") {
		try {
			await finalize.submit({
				doctype: props.doctype,
				name: props.id,
				docstatus: action === "submit" ? 1 : 2,
				expected_modified: documentResource.doc?.modified,
			})
		} catch {
			// finalize.onError already toasted the server's reason
		}
		// render what the server did, whether or not it agreed
		await reloadDoc()
		return
	}

	await documentResource.setValue.submit({ ...formModel.value })
	await documentResource.get.promise
	resetForm()
}

function saveForm() {
	emit("validateForm")
	if (props.saveError) {
		formErrorMessage.value = props.saveError
		return
	}

	if (props.id) {
		handleDocUpdate()
	} else {
		handleDocInsert()
	}
}

function submitOrCancelForm() {
	if (isFormDirty.value) return

	if (formModel.value.docstatus === 0) {
		emit("validateForm")
		showSubmitDialog.value = true
	} else if (formModel.value.docstatus === 1) {
		showCancelDialog.value = true
	}
}

function handleDocDelete() {
	documentResource.delete.submit()
	showDeleteDialog.value = false
}

async function reloadDoc() {
	await documentResource.reload()
	resetForm()
}

function resetForm() {
	formModel.value = { ...documentResource.doc }
	nextTick(() => {
		isFormDirty.value = false
		isFormUpdated.value = true
		emit("formReloaded")
	})
}
function handleDownload() {
	if (!props.id) return
	downloadPDF({
		doctype: props.doctype,
		docname: props.id,
		filename: props.id,
	})
}

async function setFormattedCurrency() {
	const companyCurrency = await getCompanyCurrency(formModel.value.company)

	props.fields.forEach((field) => {
		if (field.fieldtype !== "Currency") return
		if (!(field.readOnly || isFormReadOnly.value)) return

		if (field.options === "currency") {
			formModel.value[field.fieldname] = formatCurrency(
				formModel.value[field.fieldname],
				formModel.value.currency
			)
		} else {
			formModel.value[field.fieldname] = formatCurrency(
				formModel.value[field.fieldname],
				companyCurrency
			)
		}
	})
}

const isFormReady = computed(() => {
	if (!props.id) return true

	return !documentResource.get.loading && documentResource.doc
})

const isFormReadOnly = computed(() => {
	if (!isFormReady.value) return true
	if (!props.id) return false

	// submitted & cancelled docs are read only
	if (formModel.value.docstatus !== 0) return true

	// read only due to workflow based on current user's roles
	if (workflow.value?.isReadOnly(formModel.value)) return true

	return false
})

onMounted(async () => {
	if (props.id) {
		await documentResource.get.promise
		formModel.value = { ...documentResource.doc }
		await docPermissions.reload()
		await permittedWriteFields.reload()
		await attachedFiles.reload()
		await setFormattedCurrency()

		// workflow
		workflow.value = useWorkflow(props.doctype)

		isFormDirty.value = false
	}
})
</script>
