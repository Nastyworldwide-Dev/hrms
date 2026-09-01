<template>
	<div v-if="document?.doc" class="bg-ground w-full flex flex-col pb-5 max-h-sheet">
		<!-- Header -->
		<div
			class="w-full flex flex-row gap-2 pt-6 pb-4 px-4 border-b border-divider justify-between items-center sticky top-0 z-overlay bg-ground"
		>
			<div class="flex flex-col gap-1">
				<div class="g-eyebrow">{{ __("Request") }}</div>
				<span class="text-inkbase font-extrabold text-stat-number leading-tight">
					{{ __(document?.doctype) }}
				</span>
			</div>
			<FeatherIcon
				v-if="props.showOpenForm"
				name="external-link"
				class="h-4 w-4 text-ink-600 cursor-pointer shrink-0"
				@click="openFormView"
			/>
		</div>

		<!-- Request Summary -->
		<div class="w-full px-4 overflow-auto">
			<div class="flex flex-col w-full">
				<div
					v-for="field in fieldsWithValues"
					:key="field.fieldname"
					:class="[
						['Small Text', 'Text', 'Long Text', 'Table', 'geolocation'].includes(field.fieldtype)
							? 'flex-col gap-1'
							: 'flex-row items-center justify-between gap-4',
						'flex w-full py-3 border-b border-divider last:border-b-0',
					]"
				>
					<div class="text-ink-600 text-xs shrink-0">
						{{ __(field.label, null, props.modelValue?.doctype) }}
					</div>
					<component
						v-if="field.fieldtype === 'Table'"
						:is="field.component"
						:doc="document?.doc"
					/>
					<FormattedField
						v-else
						class="text-sm text-inkbase text-right"
						:value="field.value"
						:fieldtype="field.fieldtype"
						:fieldname="field.fieldname"
					/>
				</div>

				<!-- Attachments -->
				<div class="flex flex-col gap-2 w-full py-3" v-if="attachedFiles?.data?.length">
					<div class="g-eyebrow">{{ __("Attachments") }}</div>
					<ul class="w-full flex flex-col items-center gap-2">
						<li
							class="bg-surface border border-divider p-2 w-full"
							v-for="file in attachedFiles.data"
							:key="file.name"
						>
							<div class="flex flex-row items-center justify-between text-inkbase text-sm">
								<span class="grow" @click="showFilePreview(file)">
									{{ file.file_name || file.name }}
								</span>
							</div>
						</li>
					</ul>
				</div>
			</div>
		</div>

		<!-- Actions -->
		<WorkflowActionSheet
			v-if="workflow?.hasWorkflow"
			:doc="document.doc"
			:workflow="workflow"
			view="actionSheet"
		/>

		<div
			v-else-if="
				['Open', 'Draft'].includes(document?.doc?.[approvalField]) && hasPermission('approval')
			"
			class="flex w-full flex-row items-center justify-between gap-3 sticky bottom-0 border-t border-divider bg-ground z-overlay p-4"
		>
			<Button
				@click="updateDocumentStatus({ status: 'Rejected' })"
				:loading="submitting"
				:disabled="submitting"
				class="w-full py-5 !bg-transparent !border !border-red-600 !text-red-600"
				variant="subtle"
				theme="red"
			>
				<template #prefix>
					<FeatherIcon name="x" class="w-4" />
				</template>
				{{ __("Reject") }}
			</Button>

			<Button
				@click="updateDocumentStatus({ status: 'Approved' })"
				:loading="submitting"
				:disabled="submitting"
				class="w-full py-5 !bg-accent-ink hover:!bg-accent-600 !text-ground !border-none"
				variant="solid"
			>
				<template #prefix>
					<FeatherIcon name="check" class="w-4" />
				</template>
				{{ __("Approve") }}
			</Button>
		</div>

		<div
			v-else-if="
				document?.doc?.docstatus === 0 &&
				['Approved', 'Rejected'].includes(document?.doc?.[approvalField]) &&
				hasPermission('submit')
			"
			class="flex w-full flex-row items-center justify-between gap-3 sticky bottom-0 border-t border-divider bg-ground z-overlay p-4"
		>
			<Button
				@click="updateDocumentStatus({ docstatus: 1 })"
				:loading="submitting"
				:disabled="submitting"
				class="w-full py-5 !bg-accent-ink hover:!bg-accent-600 !text-ground !border-none"
				variant="solid"
			>
				{{ __("Submit") }}
			</Button>
		</div>

		<div
			v-else-if="document?.doc?.docstatus === 1 && hasPermission('cancel')"
			class="flex w-full flex-row items-center justify-between gap-3 sticky bottom-0 border-t border-divider bg-ground z-overlay p-4"
		>
			<Button
				@click="updateDocumentStatus({ docstatus: 2 })"
				:loading="submitting"
				:disabled="submitting"
				class="w-full py-5 !bg-transparent !border !border-red-600 !text-red-600"
				variant="subtle"
				theme="red"
			>
				<template #prefix>
					<FeatherIcon name="x" class="w-4" />
				</template>
				{{ __("Cancel") }}
			</Button>
		</div>

		<!-- File Preview Modal -->
		<ion-modal ref="modal" :is-open="showPreviewModal" @didDismiss="showPreviewModal = false">
			<FilePreviewModal :file="selectedFile" />
		</ion-modal>
	</div>
</template>

<script setup>
import { computed, inject, ref, defineAsyncComponent, onMounted } from "vue"
import { IonModal, modalController } from "@ionic/vue"
import { useRouter } from "vue-router"
import { toast, createDocumentResource, createResource, FeatherIcon } from "frappe-ui"

import FormattedField from "@/components/FormattedField.vue"
import FilePreviewModal from "@/components/FilePreviewModal.vue"
import WorkflowActionSheet from "@/components/WorkflowActionSheet.vue"

import { getCompanyCurrency } from "@/data/currencies"
import { settings } from "@/data/settings"
import { formatCurrency } from "@/utils/formatters"

import useWorkflow from "@/composables/workflow"

const __ = inject("$translate")

const props = defineProps({
	fields: {
		type: Array,
		required: true,
	},
	showOpenForm: {
		type: Boolean,
		default: true,
	},
	modelValue: {
		type: Object,
		required: true,
	},
})
const router = useRouter()

let showPreviewModal = ref(false)
let selectedFile = ref({})
let workflow = ref(null)

function showFilePreview(fileObj) {
	selectedFile.value = fileObj
	showPreviewModal.value = true
}

const document = createDocumentResource({
	doctype: props.modelValue.doctype,
	name: props.modelValue.name,
	auto: true,
	onSuccess(_doc) {
		attachedFiles.reload()
	},
})

const attachedFiles = createResource({
	url: "hrms.api.get_attachments",
	params: {
		dt: props.modelValue.doctype,
		dn: props.modelValue.name,
	},
})

const docPermissions = createResource({
	url: "frappe.client.get_doc_permissions",
	params: { doctype: props.modelValue.doctype, docname: props.modelValue.name },
	auto: true,
})

const permittedWriteFields = createResource({
	url: "hrms.api.get_permitted_fields_for_write",
	params: { doctype: props.modelValue.doctype },
	auto: true,
})

// Doctypes whose `on_submit` refuses an undecided document, so deciding and
// finalizing are one transition rather than two. The server owns it —
// hrms/api/approval.py holds the same list and is the authority; this copy only
// decides which call to make.
const DECIDE_THEN_SUBMIT = [
	"Leave Application",
	"Shift Request",
	"Expense Claim",
	// These three gained a status field on 26 Aug 2026. Before that they were
	// submittable with no decision field, so the Approve/Reject block — which
	// renders on doc.status being Open/Draft — never appeared and an approver
	// could approve but never decline.
	"OT Request",
	"Attendance Request",
	"Replacement Leave Claim",
]

const decision = createResource({ url: "hrms.api.approval.decide" })
// Submit and cancel for requests with no decision field. NOT document.setValue:
// frappe.client.set_value refuses to write docstatus ("Cannot edit standard
// fields"), correctly — moving docstatus is a TRANSITION, not an edit, and it
// has to run validate/before_submit/on_submit. The old call threw, a toast
// flashed on a phone, and the document stayed a draft while the approver
// believed they had approved it.
const finalize = createResource({ url: "hrms.api.approval.finalize" })

// True while any decision/transition is in flight. Bound to the action
// buttons so a consequential, irreversible tap shows a loading state and
// cannot be double-fired — the backend is idempotent and row-locked, but the
// UI should still say "working" and refuse a second tap.
const submitting = computed(
	() => decision.loading || finalize.loading || document.setValue?.loading
)

const sessionEmployee = inject("$employee")

function hasPermission(action) {
	if (action === "approval" && props.modelValue.doctype === "Leave Application") {
		// prevent self leave approval
		const isSelfLeave = document?.doc?.employee === sessionEmployee?.data?.name
		if (isSelfLeave && settings.data?.prevent_self_leave_approval) return false
		return permittedWriteFields.data?.includes(approvalField.value)
	}
	return docPermissions.data?.permissions[action]
}

const currency = computed(() => {
	let docCurrency = document?.doc?.currency

	if (!docCurrency && document?.doc?.company) {
		docCurrency = getCompanyCurrency(document?.doc?.company)
	}
	return docCurrency
})

const fieldsWithValues = computed(() => {
	return props.fields.filter((field) => {
		if (field.fieldtype === "Currency") {
			field.value = formatCurrency(document.doc?.[field.fieldname], currency.value)
		} else {
			if (field.fieldtype === "Table") {
				// dynamically loading child table component as per config
				// does not work with @ alias due to vite's import analysis
				field.component = defineAsyncComponent(() =>
					import(`../components/${field.componentName}.vue`)
				)
			}
			field.value = document?.doc?.[field.fieldname] || props.modelValue[field.fieldname]
		}

		return field.value
	})
})

const approvalField = computed(() => {
	return props.modelValue.doctype === "Expense Claim" ? "approval_status" : "status"
})

const getSuccessMessage = ({ status = "", docstatus = 0 }) => {
	if (status) {
		return __("{0} successfully!", [__(status)])
	} else if (docstatus) {
		return __("Document {0} successfully!", [docstatus === 1 ? __("submitted") : __("cancelled")])
	}
}

const getFailureMessage = ({ status = "", docstatus = 0 }) => {
	if (status) {
		return __("{0} failed!", [status === __("Approved") ? __("Approval") : __("Rejection")])
	} else if (docstatus) {
		return __("Document {0} failed!", [docstatus === 1 ? __("submission") : __("cancellation")])
	}
}

const onActionSuccess = ({ status, docstatus, dismiss }) => {
	if (dismiss) modalController.dismiss()
	toast({
		title: __("Success"),
		text: getSuccessMessage({ status, docstatus }),
		icon: "check-circle",
		position: "bottom-center",
		iconClasses: "text-green-500",
	})
}

const onActionError =
	({ status, docstatus }) =>
	(error) => {
		// the server's message says WHY (permissions, validation) —
		// a bare "Approval failed!" is undebuggable from the field
		console.warn("[RequestActionSheet] action failed:", error)
		toast({
			title: __("Error"),
			text: error?.messages?.[0] || getFailureMessage({ status, docstatus }),
			icon: "alert-circle",
			position: "bottom-center",
			iconClasses: "text-red-500",
		})
	}

const updateDocumentStatus = ({ status = "", docstatus = 0 }) => {
	// A decision goes to the server as a decision. This used to be assembled
	// here — status, plus docstatus=1 but only for "Approved" and only when a
	// client-side permission read said the user could submit. Rejections
	// therefore never finalized at all, and an approval quietly degraded into a
	// half-transitioned document whenever that read said no or had not loaded,
	// leaving HR to press Submit on something already approved.
	if (status && DECIDE_THEN_SUBMIT.includes(props.modelValue.doctype)) {
		return decision.submit(
			{
				doctype: props.modelValue.doctype,
				name: props.modelValue.name,
				status,
			},
			{
				onSuccess(result) {
					// render what the server did, not what we asked for
					document.reload?.()
					onActionSuccess({
						status,
						docstatus: result?.docstatus ?? 1,
						dismiss: true,
					})
				},
				onError: onActionError({ status, docstatus: 0 }),
			}
		)
	}

	// plain submit / cancel. Today nothing else reaches here: the Approve and
	// Reject buttons only render when the document HAS a decision field, and the
	// three doctypes that have one are all listed above. `status` is still
	// forwarded so a fourth doctype added to the sheet degrades to the old
	// behaviour rather than silently dropping the decision.
	// A decision on a doctype that HAS a field, but is not in the list above,
	// still needs that field written — keep the old path for it.
	if (status) {
		return document.setValue.submit(
			{ [approvalField.value]: status },
			{
				onSuccess() {
					onActionSuccess({ status, docstatus: 0, dismiss: false })
				},
				onError: onActionError({ status, docstatus: 0 }),
			}
		)
	}

	// Pure transition. The server performs it and tells us what it did.
	finalize.submit(
		{ doctype: props.modelValue.doctype, name: props.modelValue.name, docstatus },
		{
			onSuccess(result) {
				document.reload?.()
				onActionSuccess({
					status,
					docstatus: result?.docstatus ?? docstatus,
					dismiss: true,
				})
			},
			onError: onActionError({ status, docstatus }),
		}
	)
}

const openFormView = () => {
	modalController.dismiss()
	router.push({
		name: `${props.modelValue.doctype.replace(/\s+/g, "")}DetailView`,
		params: { id: props.modelValue.name },
	})
}

onMounted(() => {
	workflow.value = useWorkflow(props.modelValue.doctype)
})
</script>

<style scoped>
ion-modal {
	--height: 100%;
}
</style>
