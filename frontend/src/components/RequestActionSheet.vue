<template>
	<!-- alpha.14 (owner screenshot, 27 Sep 2026): this sheet drew its own black
	     box inside the sheet, 12 pt grey labels, a name cut off at the right
	     edge and the note as a field inside a row. It is now what every other
	     sheet is: groups on the sheet's own grouped background, 17 pt rows,
	     long values under their label (v-value-row), long text stacked. -->
	<div v-if="document?.doc" class="g-form-body g-request-sheet">
		<!-- What the request is and WHEN (alpha.11), with the open-form link in
		     the header, as iOS puts an action beside a section title. -->
		<section class="g-form-section">
			<div class="g-exp-head">
				<h2 class="g-form-section__title">{{ __("Request") }}</h2>
				<GIconButton v-if="props.showOpenForm" :label="__('Open the form')" @click="openFormView">
					<ExternalLink class="h-4 w-4" aria-hidden="true" />
				</GIconButton>
			</div>
			<GListPanel>
				<GListRow
					:label="__(kindLabel)"
					:sublabel="whenLine || ''"
					:tappable="false"
					:chevron="false"
				/>
			</GListPanel>
		</section>

		<section class="g-form-section">
			<div class="g-form-group">
				<template v-for="field in fieldsWithValues" :key="field.fieldname">
					<!-- a table (expense items) or a map is its own block in the row -->
					<div
						v-if="['Table', 'geolocation'].includes(field.fieldtype)"
						class="g-form-row g-form-row--stacked g-form-row--readonly"
					>
						<span class="g-form-row__label">
							{{ sentenceCase(__(plainLabel(field.label), null, props.modelValue?.doctype)) }}
						</span>
						<component v-if="field.fieldtype === 'Table'" :is="field.component" :doc="document?.doc" />
						<FormattedField v-else :value="field.value" :fieldtype="field.fieldtype" :fieldname="field.fieldname" />
					</div>
					<!-- long text: label on top, the words under it, as a sent reason reads -->
					<div
						v-else-if="['Small Text', 'Text', 'Long Text'].includes(field.fieldtype)"
						class="g-form-row g-form-row--stacked g-form-row--readonly"
					>
						<span class="g-form-row__label">
							{{ sentenceCase(__(plainLabel(field.label), null, props.modelValue?.doctype)) }}
						</span>
						<span class="g-form-row__value g-request-sheet__text">{{ field.value }}</span>
					</div>
					<div v-else v-value-row class="g-form-row g-form-row--readonly">
						<span class="g-form-row__label">
							{{ sentenceCase(__(plainLabel(field.label), null, props.modelValue?.doctype)) }}
						</span>
						<span class="g-form-row__value">
							<FormattedField :value="field.value" :fieldtype="field.fieldtype" :fieldname="field.fieldname" />
						</span>
					</div>
				</template>
			</div>
		</section>

		<section v-if="attachedFiles?.data?.length" class="g-form-section">
			<h2 class="g-form-section__title">{{ __("Attachments") }}</h2>
			<GAttachmentRow v-for="file in attachedFiles.data" :key="file.name" :file="file" @open="showFilePreview" />
		</section>

		<!-- Actions -->
		<!-- YOUR OWN draft: withdraw it. You can't approve your own
		     request and have no delete permission on it, so without this a saved
		     draft — already sitting in your approver's queue — was a one-way trip. -->
		<div
			v-if="
				isOwnDraft &&
				!workflow?.hasWorkflow &&
				!hasPermission('approval') &&
				!hasPermission('submit')
			"
			class="g-request-sheet__bar"
		>
			<!-- Sent is not edited (owner ruling, 27 Sep 2026): to change a request,
			     withdraw it and send a new one. -->
			<!-- At once, with Undo (owner, 29 Sep 2026, alpha.21): no "Are you
			     sure? This cannot be undone" dialog. -->
			<GButton @click="withdrawWithUndo" :label="__('Withdraw')" danger />
		</div>

		<WorkflowActionSheet
			v-else-if="workflow?.hasWorkflow"
			:doc="document.doc"
			:workflow="workflow"
			view="actionSheet"
		/>

		<div
			v-else-if="decidedAs || (isPending && hasPermission('approval'))"
			class="g-request-sheet__bar flex-col"
		>
			<!-- The live balance cannot cover these dates. Approve stays: the server
			     decides, and some leave types may go negative. -->
			<p v-if="leaveShortNotice" class="text-sm text-danger-ink" role="status">
				{{ leaveShortNotice }}
			</p>
			<!-- Approve would be refused (the server ran it as a dry run), so it
			     is not offered; this says why and what to do, before any press
			     (owner, 29 Sep 2026: guide, never error). Reject stays. -->
			<p v-if="approveBlocked" class="g-request-sheet__guide" role="status">
				{{ approveBlocked.message }}
			</p>
			<div class="flex w-full flex-row items-center justify-between gap-3">
				<!-- While the decision's mark draws, the button that was pressed
				     stays: the reloaded document already says "decided", which
				     would otherwise empty this bar before the mark is seen. -->
				<GButton
					v-if="decidedAs ? decidedAs === 'Rejected' : hasPermission('reject')"
					@click="
						confirmDecision(
							{ status: 'Rejected' },
							{
								title: __('Reject this request?'),
								body: __('The employee sees your reason. This cannot be undone.'),
								confirmLabel: __('Reject'),
							}
						)
					"
					:pending="submitting"
					:label="decidedAs === 'Rejected' ? __('Not approved') : __('Reject')"
					danger
				>
					<!-- The decision is confirmed where it was made: its mark draws
					     itself, then the sheet closes (alpha.13; Apple: Draw On). -->
					<template v-if="decidedAs === 'Rejected'" #trailing>
						<svg class="g-btn__tick g-btn__tick--cross" viewBox="0 0 24 24" aria-hidden="true">
							<path d="M7 7l10 10M17 7L7 17" />
						</svg>
					</template>
				</GButton>

				<GButton
					v-if="decidedAs ? decidedAs === 'Approved' : hasPermission('approve')"
					@click="updateDocumentStatus({ status: 'Approved' })"
					:pending="submitting"
					:label="decidedAs === 'Approved' ? __('Approved') : __('Approve')"
				>
					<template v-if="decidedAs === 'Approved'" #trailing>
						<svg class="g-btn__tick" viewBox="0 0 24 24" aria-hidden="true">
							<path d="M5 12.5l4.5 4.5L19 7.5" />
						</svg>
					</template>
				</GButton>
			</div>
		</div>

		<div
			v-else-if="
				document?.doc?.docstatus === 0 &&
				['Approved', 'Rejected'].includes(document?.doc?.[approvalField]) &&
				hasPermission('submit')
			"
			class="g-request-sheet__bar"
		>
			<GButton
				@click="updateDocumentStatus({ docstatus: 1 })"
				:pending="submitting"
				:label="__('Submit')"
			/>
		</div>

		<div
			v-else-if="
				(cancelOffer === 'approved' && approvedCancel) ||
				(cancelOffer === 'own' && hasPermission('cancel'))
			"
			class="g-request-sheet__bar"
		>
			<GButton
				@click="
					confirmDecision(
						{ docstatus: 2 },
						{
							title: __('Cancel this request?'),
							body: __('This cancels the submitted request and cannot be undone.'),
							confirmLabel: __('Cancel request'),
						}
					)
				"
				:pending="submitting"
				:label="__('Cancel')"
				danger
			/>
		</div>

		<!-- File Preview Modal -->
		<FilePreviewModal
			:is-open="showPreviewModal"
			:file="selectedFile"
			@did-dismiss="showPreviewModal = false"
		/>

		<!-- Irreversible-action confirm (Reject / Cancel). -->
		<GConfirm
			:is-open="!!pendingDecision"
			:title="pendingDecision?.title"
			:confirm-label="pendingDecision?.confirmLabel"
			:cancel-label="__('Keep')"
			:confirm-disabled="needsReason && !rejectReason.trim()"
			destructive
			@confirm="runPendingDecision"
			@cancel="pendingDecision = null"
		>
			{{ pendingDecision?.body }}
			<template v-if="needsReason" #extra>
				<!-- Audit P0-10: the employee sees this reason on their request. -->
				<GTextarea v-model="rejectReason" :label="__('Why not? (required)')" />
			</template>
		</GConfirm>


	</div>
</template>

<script setup>
import { ExternalLink } from "lucide-vue-next"
import { modalController } from "@ionic/vue"
import { createDocumentResource, createResource } from "frappe-ui"
import { gToast } from "@/components/glass/toast"
import GButton from "@/components/glass/GButton.vue"
import GIconButton from "@/components/glass/GIconButton.vue"
import GListPanel from "@/components/glass/GListPanel.vue"
import GListRow from "@/components/glass/GListRow.vue"
import { computed, defineAsyncComponent, inject, onMounted, ref } from "vue"
import { useRouter } from "vue-router"
import FilePreviewModal from "@/components/FilePreviewModal.vue"
import GAttachmentRow from "@/components/glass/GAttachmentRow.vue"
import FormattedField from "@/components/FormattedField.vue"
import GTextarea from "@/components/glass/GTextarea.vue"
import GConfirm from "@/components/glass/GConfirm.vue"
import WorkflowActionSheet from "@/components/WorkflowActionSheet.vue"
import useWorkflow from "@/composables/workflow"
import useDecisionCapability from "@/composables/decisionCapability"
import { hideRequest, unhideRequest } from "@/data/hiddenRequests"
import { reloadRequestLists } from "@/data/requestLists"
import { showUndo } from "@/data/undoBar"
import { undoable } from "@/utils/undoable"
import useApprovedCancel from "@/composables/approvedCancel"
import { getCompanyCurrency } from "@/data/currencies"
import { canOfferCancel } from "@/utils/cancelRule"
import { formatCurrency, formatHours } from "@/utils/formatters"
import { requestStatus } from "@/utils/requestStatus"
import { REQUEST_KIND } from "@/utils/requestKind"
import { requestDates } from "@/utils/requestDates"
import { plainLabel } from "@/utils/plainLabel"
import { sentenceCase } from "@/utils/sentenceCase"
import { firstMessage } from "@/utils/loudRequest"
import { shownLeaveBalance, shortLeaveNotice } from "@/utils/liveLeaveBalance"

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

// Irreversible decisions (Reject, Cancel) route through a confirm step: a
// mis-tap here permanently rejects or cancels an employee's request and the
// server transition cannot be undone from this sheet. Approve/Submit stay
// one-tap so approvers are not slowed on the common path. (RemoteApprovals
// already confirms this same class of action — this brings the sheet in line.)
const pendingDecision = ref(null)
//: A rejection must say why (audit P0-10); the server refuses one without.
const rejectReason = ref("")
const needsReason = computed(() => pendingDecision.value?.action?.status === "Rejected")
function confirmDecision(action, copy) {
	rejectReason.value = ""
	pendingDecision.value = { action, review: currentRequest(), ...copy }
}
function runPendingDecision() {
	const decision = pendingDecision.value
	const reason = rejectReason.value.trim()
	if (decision?.action?.status === "Rejected" && !reason) return
	pendingDecision.value = null
	if (decision) updateDocumentStatus({ ...decision.action, reason }, decision.review)
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

const decisionCapability = useDecisionCapability(
	() => document,
	() => ({ doctype: props.modelValue.doctype, name: props.modelValue.name }),
	() => {
		// Changed since it was opened (the employee edited it, or someone else
		// decided it): show the latest by itself, never an error to act on.
		console.info("[RequestActionSheet] request changed; reloading", props.modelValue.name)
		document.reload?.()
	}
)
//: Why Approve is not offered, in the server's plain words, or null.
const approveBlocked = computed(() => decisionCapability.blocked.value)

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
//: The decision just made, while its mark draws on the button.
const decidedAs = ref("")
//: Long enough to see the mark draw, short enough not to wait for it.
const DECIDED_MS = 650

//: In flight, or already decided while its mark draws: either way no second
//: tap may reach the server (alpha.13 kept the sheet open 650 ms for the mark).
const submitting = computed(
	() => decision.loading || finalize.loading || document.setValue?.loading || Boolean(decidedAs.value)
)

const sessionEmployee = inject("$employee")
const currentUser = inject("$user")

// HR or the approver may cancel an approved request; the employee may not
// (owner ruling, 14 Sep 2026 — see utils/cancelRule.js).
const cancelViewer = computed(() => ({
	user: currentUser?.data?.name,
	roles: currentUser?.data?.roles || [],
	employee: sessionEmployee?.data?.name,
}))
const cancelOffer = computed(() =>
	canOfferCancel(document.doc, props.modelValue?.doctype, cancelViewer.value)
)
// Approved: Cancel only when the server's guard says this viewer may.
const approvedCancel = useApprovedCancel(() =>
	cancelOffer.value === "approved"
		? {
				doctype: props.modelValue.doctype,
				name: document.doc?.name,
				modified: document.doc?.modified,
		  }
		: null
)

// Withdraw / edit your OWN draft. Employees have no delete permission on these
// doctypes, so a fenced API (owner + docstatus 0) does the removal. Employee
// Checkin is excluded on purpose — it is docstatus 0 and yours, but not a
// withdrawable request.
const WITHDRAWABLE_DOCTYPES = [
	"Attendance Request",
	"Leave Application",
	"Expense Claim",
	"Shift Request",
	"OT Request",
	"Replacement Leave Claim",
]
const isOwnDraft = computed(
	() =>
		WITHDRAWABLE_DOCTYPES.includes(props.modelValue.doctype) &&
		document?.doc?.docstatus === 0 &&
		document?.doc?.employee === sessionEmployee?.data?.name &&
		// A row mirrored from the source ERP (synced_from_instance) is read-only
		// on this hub during the parallel run — the write-block would refuse the
		// edit/delete. Don't offer actions that can only fail; it is managed on
		// the source instance.
		!document?.doc?.synced_from_instance
)

const withdraw = createResource({ url: "hrms.api.withdraw_request" })
//: Withdraw now, Undo for a few seconds, then ask the server (utils/undoable):
//: the row leaves the list at once; Undo only cancels a timer.
function withdrawWithUndo() {
	const { doctype, name } = props.modelValue
	console.info("[RequestActionSheet] withdraw with undo", name)
	hideRequest(name)
	modalController.dismiss()
	const pending = undoable(() =>
		withdraw.submit(
			{ doctype, name },
			{
				onSuccess() {
					reloadRequestLists("withdrawn")
					unhideRequest(name)
				},
				onError(err) {
					// It could not be withdrawn: it comes back, and says why.
					unhideRequest(name)
					gToast({
						title: __("Not withdrawn"),
						text: firstMessage(err, __("Could not withdraw the request.")),
						variant: "error",
					})
				},
			}
		)
	)
	showUndo(__("Withdrawn"), pending, () => unhideRequest(name))
}

function hasPermission(action) {
	if (["approval", "approve", "reject", "submit"].includes(action)) {
		if (workflow.value?.hasWorkflow) return false
		const actions = decisionCapability.actions.value
		if (action === "approval") return actions.includes("Approved") || actions.includes("Rejected")
		return actions.includes({ approve: "Approved", reject: "Rejected", submit: "Submit" }[action])
	}
	return Boolean(docPermissions.data?.permissions?.[action])
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
			// Leave Balance: the number the approve is judged by, not the filing snapshot.
			const raw =
				field.fieldname === "leave_balance" && props.modelValue.doctype === "Leave Application"
					? shownLeaveBalance(document?.doc, decisionCapability.leaveBalanceNow.value)
					: document?.doc?.[field.fieldname] || props.modelValue[field.fieldname]
			// The decision field reads from the one status rule ("Waiting",
			// "Approved"), never the raw select value ("Open") (plan P1-5).
			if (field.fieldname === approvalField.value && field.fieldtype === "Select") {
				field.value = requestStatus(props.modelValue.doctype, document.doc).label
				return field.value
			}
			// punch-derived hours Floats (claimed_hours, hours_cost…) read 5.67, not 5.669444444
			const isHours = field.fieldtype === "Float" && field.fieldname.includes("hours")
			field.value = isHours && raw ? formatHours(raw) : raw
		}

		return field.value
	})
})

//: Which day(s) this request is for; empty for types with no single date.
const whenLine = computed(() => requestDates(document?.doc))

//: The person's word for this request, not its doctype (plan P1-5).
const kindLabel = computed(() => REQUEST_KIND[document?.doctype] || document?.doctype || "")

const leaveShortNotice = computed(() =>
	props.modelValue.doctype === "Leave Application"
		? shortLeaveNotice(document?.doc, decisionCapability.leaveBalanceNow.value, __)
		: ""
)

const approvalField = computed(() => {
	return props.modelValue.doctype === "Expense Claim" ? "approval_status" : "status"
})

// Whether the request still needs a decision — the shared rule, so the sheet
// and the list chip cannot disagree. The server's get_decision_actions is
// still the authority on WHO may decide (hasPermission).
const isPending = computed(
	() => Boolean(document?.doc) && requestStatus(props.modelValue.doctype, document.doc).pending
)

const getSuccessMessage = ({ status = "", docstatus = 0 }) => {
	if (status) {
		return __("{0} successfully!", [__(status)])
	} else if (docstatus) {
		return __("Document {0} successfully!", [docstatus === 1 ? __("submitted") : __("cancelled")])
	}
}

const getFailureMessage = ({ status = "", docstatus = 0 }) => {
	if (status) {
		return __("{0} failed!", [status === "Approved" ? __("Approval") : __("Rejection")])
	} else if (docstatus) {
		return __("Document {0} failed!", [docstatus === 1 ? __("submission") : __("cancellation")])
	}
}


const onActionSuccess = ({ status, docstatus, dismiss }) => {
	if (dismiss && status) {
		decidedAs.value = status
		console.info("[RequestActionSheet] decided:", status)
		setTimeout(() => modalController.dismiss(), DECIDED_MS)
	} else if (dismiss) modalController.dismiss()
	gToast({
		title: __("Success"),
		text: getSuccessMessage({ status, docstatus }),
		variant: "success",
	})
}

const onActionError =
	({ status, docstatus }) =>
	(error) => {
		document.reload?.()
		// the server's message says WHY (permissions, validation) —
		// a bare "Approval failed!" is undebuggable from the field
		console.warn("[RequestActionSheet] action failed:", error)
		gToast({
			title: __("Error"),
			text: firstMessage(error, getFailureMessage({ status, docstatus })),
			variant: "error",
		})
	}

const currentRequest = () => ({
	doctype: document.doc?.doctype,
	name: document.doc?.name,
	expected_modified: document.doc?.modified,
})

const updateDocumentStatus = (
	{ status = "", docstatus = 0, reason = "" },
	review = currentRequest()
) => {
	if (
		submitting.value ||
		review.doctype !== props.modelValue.doctype ||
		review.name !== props.modelValue.name ||
		JSON.stringify(review) !== JSON.stringify(currentRequest()) ||
		(status && !hasPermission(status === "Approved" ? "approve" : "reject")) ||
		(docstatus === 1 && !hasPermission("submit"))
	)
		return
	// A decision goes to the server as a decision. This used to be assembled
	// here — status, plus docstatus=1 but only for "Approved" and only when a
	// client-side permission read said the user could submit. Rejections
	// therefore never finalized at all, and an approval quietly degraded into a
	// half-transitioned document whenever that read said no or had not loaded,
	// leaving HR to press Submit on something already approved.
	// Any decision goes to the server as a decision — hrms.api.approval.decide is
	// the authority (its decision_field allow-list throws for a non-approvable type),
	// so there is no client list to drift and no half-transition path. The Approve/
	// Reject buttons only render on a doc that HAS a decision field anyway.
	if (status) {
		return decision.submit(
			{
				...review,
				status,
				reason: status === "Rejected" ? reason : undefined,
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

	// Pure transition (no decision — a plain submit/cancel). The server performs it
	// and tells us what it did.
	finalize.submit(
		{
			...review,
			docstatus,
		},
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
