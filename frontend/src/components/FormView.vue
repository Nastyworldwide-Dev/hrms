<template>
	<div class="flex flex-col h-full w-full form-view-root" v-if="isFormReady">
		<!-- No bg-ground here (8.4): this container is full-bleed over the page,
	     and an opaque page-colour fill painted straight over the light field,
	     so every form and detail screen rendered flat. The sticky header and
	     footer below KEEP their fill — they need to be opaque as content
	     scrolls under them. -->
		<div class="w-full h-full flex flex-col">
			<header
				class="flex flex-row bg-ground border-b border-divider py-4 px-3 items-center sticky top-0 z-sticky lg:h-16 lg:px-7 lg:py-0 lg:border-b-2"
			>
				<GIconButton :label="__('Back')" flush class="lg:hidden" @click="goBackOrHome(router)">
					<FeatherIcon name="chevron-left" class="h-5 w-5 text-inkbase" />
				</GIconButton>
				<div v-if="id" class="flex flex-row items-center gap-2 overflow-hidden grow">
					<h2
						class="text-xl font-extrabold text-inkbase tracking-tight whitespace-nowrap overflow-hidden text-ellipsis"
					>
						{{ __(props.doctype) }}
					</h2>
					<Badge :label="id" class="whitespace-nowrap text-caption" variant="outline" />
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
				</div>
				<h2
					v-else
					class="text-2xl font-extrabold text-inkbase tracking-tight lg:text-screen-title"
				>
					{{ __("New {0}", [__(doctype)], props.doctype) }}
				</h2>
				<span v-if="!id" class="g-eyebrow hidden lg:inline ml-auto">
					{{ dateKicker }}
				</span>
			</header>

			<!-- Form -->
			<div class="grow overflow-y-auto">
				<div class="w-full sm:max-w-2xl sm:mx-auto">
					<button
						type="button"
						class="g-eyebrow hidden lg:flex items-center gap-2 px-4 pt-6 hover:text-inkbase"
						@click="goBackOrHome(router)"
					>
						<FeatherIcon name="arrow-left" class="h-4 w-4" />
						{{ __("Back") }}
					</button>
					<!-- Tabs -->
					<template v-if="tabbedView">
						<div
							class="px-4 sticky top-0 z-overlay bg-ground text-sm font-medium text-center text-ink-600 border-b border-divider"
						>
							<ul class="flex -mb-px overflow-auto hide-scrollbar">
								<li class="mr-2 whitespace-nowrap" v-for="tab in tabs" :key="tab.name">
									<button
										@click="activeTab = tab.name"
										class="inline-block py-4 px-2 border-b-2 border-transparent"
										:class="[
											activeTab === tab.name
												? '!text-accent-ink !border-accent-ink !font-extrabold'
												: 'hover:text-inkbase hover:border-divider',
										]"
									>
										{{ __(tab.name, null, props.doctype) }}
									</button>
								</li>
							</ul>
						</div>

						<template v-for="(fieldList, tabName, index) in tabFields" :key="tabName">
							<div v-show="tabName === activeTab" class="flex flex-col space-y-4 p-4">
								<template v-for="field in fieldList" :key="field.fieldname">
									<slot
										v-if="field.fieldtype == 'Table'"
										:name="field.fieldname"
										:isFormReadOnly="isFormReadOnly"
									></slot>

									<FormField
										v-else
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
										:addSectionPadding="fieldList[0].name !== field.name"
									/>
								</template>

								<!-- Attachment upload -->
								<div
									class="flex flex-row gap-2 items-center justify-center p-5"
									v-if="isFileUploading"
								>
									<LoadingIndicator class="w-3 h-3 text-accent-ink" />
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

					<div class="flex flex-col space-y-4 p-4" v-else>
						<FormField
							v-for="field in props.fields"
							:key="field.name"
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

						<!-- Attachment upload -->
						<div
							class="flex flex-row gap-2 items-center justify-center p-5"
							v-if="isFileUploading"
						>
							<LoadingIndicator class="w-3 h-3 text-accent-ink" />
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
				<div class="w-full sm:max-w-2xl sm:mx-auto">
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

			<!-- save/submit/cancel -->
			<div
				v-else-if="isFormDirty || (!workflow?.hasWorkflow && formButton)"
				class="px-4 pt-4 pb-4 standalone:pb-safe-bottom bg-ground sticky bottom-0 w-full z-40 border-t border-divider"
			>
				<div class="w-full sm:max-w-2xl sm:mx-auto">
					<ErrorMessage
						class="mb-2"
						:message="
							formErrorMessage || docList?.insert?.error || documentResource?.setValue?.error
						"
					/>

					<!-- GButton, not a frappe-ui Button painted with utilities (8.17).
				     This was the ONLY primary action in the product that bypassed
				     the primary component, which is precisely why it was the only
				     one that drifted: it wrote `!bg-accent` expecting the brand and
				     got --accent-ink, dark olive on light. GButton resolves
				     --g-brand directly, so it cannot. -->
					<GButton
						:label="__(formButton)"
						:pending-label="__('Saving…')"
						:pending="docList.insert.loading || documentResource?.setValue?.loading"
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
		<header
			class="flex flex-row bg-ground border-b border-divider py-4 px-3 items-center sticky top-0 z-sticky lg:h-16 lg:px-7 lg:py-0 lg:border-b-2"
		>
			<GIconButton :label="__('Back')" flush @click="goBackOrHome(router)">
				<FeatherIcon name="chevron-left" class="h-5 w-5 text-inkbase" />
			</GIconButton>
			<h2 class="text-xl font-extrabold text-inkbase tracking-tight ml-1 truncate">
				{{ __(props.doctype) }}
			</h2>
		</header>
		<div class="grow overflow-y-auto flex items-center justify-center p-6">
			<div
				v-if="documentResource.get.loading"
				class="flex flex-col items-center gap-3 text-ink-600"
			>
				<LoadingIndicator class="h-6 w-6 text-accent-ink" />
				<span class="text-caption">{{ __("Loading…") }}</span>
			</div>
			<GEmptyState
				v-else
				:title="__('Could not open this {0}', [__(props.doctype)])"
				:body="
					__('It may have been removed, or you may not have access. Check your connection and try again.')
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
	<GConfirm
		:is-open="showDeleteDialog"
		:title="__('Delete {0}', [__(props.doctype)])"
		:confirm-label="__('Delete')"
		:cancel-label="__('Cancel')"
		destructive
		@confirm="handleDocDelete"
		@cancel="showDeleteDialog = false"
	>
		{{ __("Are you sure you want to delete the {0}", [__(props.doctype)]) }}
		{{ formModel.name }}?
	</GConfirm>

	<GConfirm
		:is-open="showSubmitDialog"
		:title="__('Confirm')"
		:confirm-label="__('Yes')"
		:cancel-label="__('No')"
		@confirm="handleDocUpdate('submit')"
		@cancel="showSubmitDialog = false"
	>
		{{ __("Permanently submit {0}", [__(props.doctype)]) }}
		{{ formModel.name }}?
	</GConfirm>

	<Dialog v-model="showCancelDialog">
		<template #body-title>
			<h2 class="text-xl font-bold">{{ __("Confirm") }}</h2>
		</template>
		<template #body-content>
			<p>
				{{ __("Permanently cancel {0}", [__(props.doctype)]) }}
				<span class="font-bold">{{ formModel.name }}</span
				>?
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
import GButton from "@/components/glass/GButton.vue"
import GConfirm from "@/components/glass/GConfirm.vue"
import { computed, inject, nextTick, onMounted, ref, watch } from "vue"
import { useRouter } from "vue-router"
import GIconButton from "@/components/glass/GIconButton.vue"
import GStatusChip from "@/components/glass/GStatusChip.vue"
import GEmptyState from "@/components/glass/GEmptyState.vue"

import { goBackOrHome } from "@/utils/navigation"
import {
	ErrorMessage,
	Badge,
	FeatherIcon,
	createListResource,
	createDocumentResource,
	toast,
	createResource,
	Dropdown,
	Dialog,
	LoadingIndicator,
} from "frappe-ui"
import FormField from "@/components/FormField.vue"
import FileUploaderView from "@/components/FileUploaderView.vue"
import WorkflowActionSheet from "@/components/WorkflowActionSheet.vue"

import { FileAttachment, guessStatusColor } from "@/composables"
import useWorkflow from "@/composables/workflow"
import { getCompanyCurrency } from "@/data/currencies"
import { formatCurrency } from "@/utils/formatters"
import { useDownloadPDF } from "@/utils/commonUtils"

const props = defineProps({
	doctype: {
		type: String,
		required: true,
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
const $dayjs = inject("$dayjs")
const employee = inject("$employee")

// Uppercase long date shown on the lg+ header (e.g. "THURSDAY, 23 JULY 2026").
const dateKicker = computed(() => $dayjs().format("dddd, D MMMM YYYY").toUpperCase())

let activeTab = ref(props.tabs?.[0].name)
let fileAttachments = ref([])
let statusColor = ref("")
let formErrorMessage = ref("")
let isFormDirty = ref(false)
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

	return formModel.value.status || formModel.value.approval_status
})

watch(
	() => formModel.value,
	() => {
		if (!props.id) return

		if (isFormReady.value && !isFormUpdated.value) {
			isFormDirty.value = true
		} else if (isFormUpdated.value) {
			isFormUpdated.value = false
		}
	},
	{ deep: true }
)

watch(
	() => status.value,
	async (value) => {
		if (!value) return
		statusColor.value = await guessStatusColor(props.doctype, status.value)
	},
	{ immediate: true }
)

const tabFields = computed(() => {
	let fieldsByTab = {}
	let fieldList = []
	let firstFieldIndex = 0
	let lastFieldIndex = 0

	props.tabs?.forEach((tab) => {
		lastFieldIndex = props.fields.findIndex((field) => field.fieldname === tab.lastField)
		fieldList = props.fields.slice(firstFieldIndex, lastFieldIndex + 1)
		fieldsByTab[tab.name] = fieldList
		firstFieldIndex = lastFieldIndex + 1
	})

	return fieldsByTab
})

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
				text: __("{0} created successfully!", [__(props.doctype)]),
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
		onError() {
			toast({
				title: __("Error"),
				text: __("Error creating {0}", [__(props.doctype)]),
				icon: "alert-circle",
				position: "bottom-center",
				iconClasses: "text-red-500",
			})
			console.log(`Error creating ${props.doctype}`)
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
				text: __("{0} updated successfully!", [__(props.doctype)]),
				icon: "check-circle",
				position: "bottom-center",
				iconClasses: "text-green-500",
			})
		},
		onError() {
			toast({
				title: __("Error"),
				text: __("Error updating {0}", [__(props.doctype)]),
				icon: "alert-circle",
				position: "bottom-center",
				iconClasses: "text-red-500",
			})
			console.log(`Error updating ${props.doctype}`)
		},
	},
	delete: {
		onSuccess() {
			router.back()
			toast({
				title: __("Success"),
				text: __("{0} deleted successfully!", [__(props.doctype)]),
				icon: "check-circle",
				position: "bottom-center",
				iconClasses: "text-green-500",
			})
		},
		onError() {
			toast({
				title: __("Error"),
				text: __("Error deleting {0}", [__(props.doctype)]),
				icon: "alert-circle",
				position: "bottom-center",
				iconClasses: "text-red-500",
			})
			console.log(`Error deleting ${props.doctype}`)
		},
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

// doctypes whose server controller rejects submit until the approver has
// set one of these statuses — offering Submit earlier can only ever error
const SUBMIT_REQUIRES_STATUS = {
	"Leave Application": ["Approved", "Rejected"],
	"Shift Request": ["Approved", "Rejected"],
}

const formButton = computed(() => {
	if (!props.showFormButton) return null

	if (props.id && props.isSubmittable && !isFormDirty.value) {
		const requiredStatuses = SUBMIT_REQUIRES_STATUS[props.doctype]
		const submitBlocked =
			(requiredStatuses && !requiredStatuses.includes(formModel.value.status)) ||
			// Attendance Request: submitting IS the approval — the server rejects
			// self-submission, so never offer Submit on your own request
			(props.doctype === "Attendance Request" && formModel.value.employee === employee.data?.name)

		if (formModel.value.docstatus === 0 && hasPermission("submit") && !submitBlocked) {
			return "Submit"
		} else if (formModel.value.docstatus === 1 && hasPermission("cancel")) {
			return "Cancel"
		}
		// submitted-and-cancel-blocked, or any other docstatus: no button.
		return null
	} else if (formModel.value.docstatus !== 2) {
		return "Save"
	}
	return null
})

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
		.filter((field) => field.reqd && !field.hidden && !formModel.value[field.fieldname])
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
	if (documentResource.doc) {
		let params = { ...formModel.value }

		if (!validateMandatoryFields()) return

		if (action == "submit") {
			params.docstatus = 1
		} else if (action == "cancel") {
			params.docstatus = 2
		}

		await documentResource.setValue.submit(params)
		await documentResource.get.promise
		resetForm()
	}

	if (action === "submit") showSubmitDialog.value = false
	else if (action === "cancel") showCancelDialog.value = false
}

function saveForm() {
	emit("validateForm")

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

const isFormReadOnly = computed(() => {
	if (!isFormReady.value) return true
	if (!props.id) return false

	// submitted & cancelled docs are read only
	if (formModel.value.docstatus !== 0) return true

	// read only due to workflow based on current user's roles
	if (workflow.value?.isReadOnly(formModel.value)) return true

	return false
})

const isFormReady = computed(() => {
	if (!props.id) return true

	return !documentResource.get.loading && documentResource.doc
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

<style scoped>
/* Modernist form controls: surface fill, hairline divider border, square, 14px. */
.form-view-root :deep(input:not([type="checkbox"]):not([type="radio"])),
.form-view-root :deep(textarea),
.form-view-root :deep(select) {
	background-color: var(--g-glass-fill-fallback);
	border: 1px solid var(--g-hair);
	border-radius: 0;
	font-size: 14px;
	color: var(--g-ink);
}
.form-view-root :deep(input:not([type="checkbox"]):not([type="radio"]):focus),
.form-view-root :deep(textarea:focus),
.form-view-root :deep(select:focus) {
	border-color: var(--g-accent-ink);
	box-shadow: none;
	outline: none;
}
</style>
