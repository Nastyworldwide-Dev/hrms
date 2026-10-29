<template>
	<!-- One iOS section (alpha.9 D8): a header with its Add action, the items
	     as rows in ONE group, the total as the footer. It was a loose header
	     row with a bold total, over a hand-drawn table. -->
	<section class="g-form-section">
		<div class="g-exp-head">
			<h2 class="g-form-section__title">{{ __("Expenses") }}</h2>
			<GIconButton
				v-if="!isReadOnly"
				id="add-expense-modal"
				:label="__('Add an expense')"
				@click="openModal()"
			>
				<Plus class="w-4" />
			</GIconButton>
		</div>
		<!-- §6.3: an expense figure is a number someone disputes with their
		     manager, so it sits on the group's opaque fill, never translucent. -->
		<GListPanel v-if="expenseClaim.expenses?.length">
			<GListRow
				v-for="(item, idx) in expenseClaim.expenses"
				:key="idx"
				:label="__(item.expense_type)"
				:sublabel="itemLine(item)"
				:amount="formatCurrency(item.amount, expenseClaim.currency)"
				@click="openModal(item, idx)"
			/>
		</GListPanel>
		<!-- The first Add is a labelled button, not the header's small + alone
		     (UX review 21 Oct 2026, F4). -->
		<GEmptyState v-else :title="__('No expenses added')" :body="__('Add each item you paid for.')">
			<template v-if="!isReadOnly" #action>
				<!-- ghost: Send is this screen's one filled action (§18) -->
				<GGhostButton :label="__('Add expense')" @click="openModal()" />
			</template>
		</GEmptyState>
		<p v-if="expenseClaim.expenses?.length" class="g-form-footer">
			{{
				__("Total {0}", [formatCurrency(expenseClaim.total_claimed_amount, expenseClaim.currency)])
			}}
		</p>
	</section>

	<GModal :is-open="isModalOpen" :title="modalTitle" @did-dismiss="resetSelectedItem()">
		<!-- Add Expense Action Sheet -->
		<div class="w-full flex flex-col pb-5">
			<div class="w-full flex flex-col items-center justify-center gap-5 p-4 max-h-[80vh]">
				<div class="w-full overflow-y-auto expense-fields">
					<!-- A failed load is not an empty form (alpha.38 L1b): the sheet said
					     nothing and "Add expense" then added a line with no fields. -->
					<ResourceError
						v-if="expensesTableFields.error"
						:resource="expensesTableFields"
						what="the expense form"
					/>
					<ResourceError
						v-else-if="claimTypesResource.error"
						:resource="claimTypesResource"
						what="the expense types"
					/>
					<section v-for="group in sheetGroups" :key="group.key" class="g-form-section mb-4">
						<h2 v-if="group.label" class="g-form-section__title">
							{{ sentenceCase(__(group.label, null, "Expense Claim Detail")) }}
						</h2>
						<template v-for="(segment, s) in group.segments" :key="s">
							<!-- The line's own receipt (owner, 20 Oct 2026): its own group, right
							     after the description. Not a FormField: the Attach field is
							     filtered out of the fields, because this one uploads at once. -->
							<ReceiptRow
								v-if="segment.kind === 'receipt'"
								v-model:url="expenseItem.receipt"
								v-model:uploading="receiptUploading"
								:required="lineNeedsReceipt"
								:readOnly="isReadOnly"
							/>
							<div v-else class="g-form-group">
								<FormField
									v-for="field in segment.fields"
									:key="field.fieldname"
									class="w-full"
									:label="__(field.label, null, 'Expense Claim Detail')"
									:fieldtype="field.fieldtype"
									:fieldname="field.fieldname"
									:options="field.options"
									:documentList="field.documentList"
									:hidden="field.hidden"
									:reqd="field.reqd"
									:default="field.default"
									:readOnly="field.read_only || isReadOnly"
									:class="field.class"
									v-model="expenseItem[field.fieldname]"
								/>
							</div>
						</template>
						<p
							v-if="
								group.segments.some((seg) => seg.fields.some((f) => f.fieldname === 'amount')) &&
								mileageLine
							"
							class="g-form-footer tabular-nums"
						>
							{{ mileageLine }}
						</p>
						<p
							v-if="
								group.segments.some((seg) =>
									seg.fields.some((f) => f.fieldname === 'distance_km')
								) && rateNote
							"
							class="g-form-footer"
							role="status"
						>
							{{ rateNote }}
						</p>
					</section>
				</div>

				<div v-if="!isReadOnly" class="flex w-full flex-col gap-3">
					<div class="flex w-full flex-row items-center justify-between gap-3">
						<GButton
							v-if="editingIdx !== null"
							class="g-btn--compact"
							danger
							:label="__('Delete')"
							@click="deleteExpenseItem()"
						/>
						<GButton
							:label="editingIdx === null ? __('Add expense') : __('Update expense')"
							:disabled="addButtonDisabled"
							:aria-describedby="addHint ? 'expense-add-hint' : undefined"
							@click="updateExpenseItem()"
						/>
					</div>
					<!-- A dimmed Add always says why: GButton swallows the tap (alpha.60) -->
					<p v-if="addHint" id="expense-add-hint" class="g-form-footer" role="status">
						{{ addHint }}
					</p>
				</div>
			</div>
		</div>
	</GModal>
</template>

<script setup>
import { Plus } from "lucide-vue-next"
import { createResource } from "frappe-ui"
import GButton from "@/components/glass/GButton.vue"
import GGhostButton from "@/components/glass/GGhostButton.vue"
import GIconButton from "@/components/glass/GIconButton.vue"
import { computed, ref, watch, inject } from "vue"

import FormField from "@/components/FormField.vue"
import GEmptyState from "@/components/glass/GEmptyState.vue"
import GListPanel from "@/components/glass/GListPanel.vue"
import GListRow from "@/components/glass/GListRow.vue"
import GModal from "@/components/glass/GModal.vue"
import ReceiptRow from "@/components/ReceiptRow.vue"
import ResourceError from "@/components/ResourceError.vue"

import { claimTypesByID, claimTypesResource } from "@/data/claims"
import { formatCurrency } from "@/utils/formatters"
import {
	missingRateNote,
	mileageAmount,
	mileageExplainer,
	withMileageFields,
} from "@/utils/expenseMileage"
import { groupFields } from "@/utils/formGroups"
import { sentenceCase } from "@/utils/sentenceCase"
import { withCostTagFields } from "@/utils/expenseCostTags"
import { GL_FIELD, withGlAccountField, withoutGlAccount } from "@/utils/expenseGlAccount"
import { addItemHint } from "@/utils/addItemHint"

import { useCurrencyConversion } from "@/composables/useCurrencyConversion"

const props = defineProps({
	expenseClaim: {
		type: Object,
		required: true,
	},
	isReadOnly: {
		type: Boolean,
		default: false,
	},
})
const emit = defineEmits(["add-expense-item", "update-expense-item", "delete-expense-item"])
const dayjs = inject("$dayjs")
const __ = inject("$translate")
const expenseItem = ref({})
const editingIdx = ref(null)

const isModalOpen = ref(false)
// the receipt is on its way to the server: Add waits for its URL
const receiptUploading = ref(false)
const isFirstRender = ref(false)

const openModal = async (item, idx) => {
	if (item) {
		// a saved line has no GL row of its own; show its type's again
		expenseItem.value = {
			...item,
			[GL_FIELD]: claimTypesByID[item.expense_type]?.gl_account || null,
		}
		editingIdx.value = idx
	}
	isFirstRender.value = true
	isModalOpen.value = true
}

const deleteExpenseItem = () => {
	emit("delete-expense-item", editingIdx.value)
	resetSelectedItem()
}

const updateExpenseItem = () => {
	// the GL row is shown, not saved: delete expenseItem[GL_FIELD] via withoutGlAccount
	const line = withoutGlAccount(expenseItem.value)
	if (editingIdx.value === null) {
		emit("add-expense-item", line)
	} else {
		emit("update-expense-item", line, editingIdx.value)
	}
	resetSelectedItem()
}

//: "Approved RM 12.50 · 21 Sep" — what came back and when, under the type.
function itemLine(item) {
	const approved = __("{0}: {1}", [
		__("Approved"),
		formatCurrency(item.sanctioned_amount || 0, props.expenseClaim.currency),
	])
	const day = item.expense_date ? dayjs(item.expense_date).format("D MMM") : ""
	const km = item.distance_km ? __("{0} km", [item.distance_km]) : ""
	const receipt = item.receipt ? __("Receipt") : ""
	return [km, approved, day, receipt].filter(Boolean).join(" · ")
}

function resetSelectedItem() {
	isFirstRender.value = false
	receiptUploading.value = false
	isModalOpen.value = false
	expenseItem.value = {}
	editingIdx.value = null
}

const expensesTableFields = createResource({
	url: "hrms.api.get_doctype_fields",
	params: { doctype: "Expense Claim Detail" },
	transform(data) {
		// alpha.6: "Sanctioned amount" is the approver's number (it follows the
		// amount, watch below), not a question for the employee. The cost tags
		// (cost center, dimensions) are NOT hidden: withCostTagFields rebuilds
		// them on purpose so staff can tag a row (d00699e3d, 15 Sep).
		const excludeFields = [
			"description_sb",
			"amounts_sb",
			"base_amount",
			"base_sanctioned_amount",
			"sanctioned_amount",
		]
		return data
			.filter((field) => !excludeFields.includes(field.fieldname))
			.map((field) => {
				// An expense line description is a short plain note, not a document.
				// Expense Claim Detail.description ships as a Text Editor (bold, image
				// and video embeds), which is the wrong field for a one-line reason —
				// render it as a plain, character-capped textarea instead.
				if (field.fieldname === "description") {
					return { ...field, fieldtype: "Small Text", maxlength: 500 }
				}
				return field
			})
	},
})
expensesTableFields.reload()

// The expense_type Link can't remote-search "Expense Claim Type": a bare Employee
// has no Desk permission on that master, so search_link (Link.vue) returns nothing
// and the dropdown is empty. Feed it the fenced get_expense_claim_types list as an
// explicit documentList — the same permission-safe pattern the expense_approver
// field uses. claimTypesResource is auto-fetched (see @/data/claims).
const expenseTypeOptions = computed(() =>
	(claimTypesResource.data || []).map((type) => ({ label: type.name, value: type.name }))
)

// Cost tags (Cost Center + Accounting Dimensions) for this claim's company,
// fenced server-side. get_doctype_fields drops those Links for an Employee
// (no Desk read on the masters), which left the section header empty.
const costTags = createResource({ url: "hrms.api.get_expense_cost_tags" })
watch(
	() => props.expenseClaim.company,
	(company) => {
		if (company) costTags.fetch({ company })
	},
	{ immediate: true }
)

// the picked type's rate per km for this company; 0 for an ordinary type
const mileageRate = computed(
	() => claimTypesByID[expenseItem.value.expense_type]?.rate_per_km || 0
)

// the picked type's GL account for this company, shown read-only under Type
const glAccount = computed(
	() => claimTypesByID[expenseItem.value.expense_type]?.gl_account || null
)

const expenseFields = computed(() =>
	withCostTagFields(
		withGlAccountField(
			withMileageFields(
				expensesTableFields.data || [],
				mileageRate.value,
				expenseItem.value.expense_type
			),
			glAccount.value,
			__
		)
			// Project is not asked (owner, 14 Oct 2026)
			.filter((field) => field.fieldname !== "project")
			// the receipt has its own row (ReceiptRow), which uploads at once
			.filter((field) => field.fieldname !== "receipt")
			.map((field) =>
				field.fieldname === "expense_type"
					? { ...field, documentList: expenseTypeOptions.value }
					: field
			),
		costTags.data
	)
)

// The receipt row sits right after the description, as its own group: the rows
// of the segment that holds the description are split around it (owner, 20 Oct 2026).
const sheetGroups = computed(() =>
	groupFields(expenseFields.value).map((group) => ({
		...group,
		segments: group.segments.flatMap((segment) => {
			const at = (segment.fields || []).findIndex((field) => field.fieldname === "description")
			if (at < 0) return [segment]
			const after = segment.fields.slice(at + 1)
			return [
				{ ...segment, fields: segment.fields.slice(0, at + 1) },
				{ kind: "receipt", fields: [] },
				...(after.length ? [{ ...segment, fields: after }] : []),
			]
		}),
	}))
)

const expenseClaimRef = computed(() => props.expenseClaim)
useCurrencyConversion(expensesTableFields, expenseClaimRef, ["amount", "sanctioned_amount"])

const modalTitle = computed(() => {
	if (props.isReadOnly) return __("Expense item")

	return editingIdx.value === null ? __("New expense item") : __("Edit expense item")
})

// A line needs its receipt unless its type switched "Receipt Required" off in Desk;
// a type the list has not loaded yet counts as required (the server decides).
const lineNeedsReceipt = computed(
	() => claimTypesByID[expenseItem.value.expense_type]?.receipt_required !== 0
)

// why Add is dimmed, in words, or "" (shown at the button). Add is dimmed
// exactly when this says something, so it never goes quiet (review of b7bb33cc9).
// expensesTableFields.data, not expenseFields: the same required list Add always checked.
const addHint = computed(() =>
	addItemHint(
		{
			fields: expensesTableFields.data,
			shown: expenseFields.value,
			item: expenseItem.value,
			needsReceipt: lineNeedsReceipt.value,
			uploading: receiptUploading.value,
			loadFailed: Boolean(expensesTableFields.error),
		},
		__
	)
)

const addButtonDisabled = computed(() => Boolean(addHint.value))

const rateNote = computed(() =>
	missingRateNote(mileageRate.value, expenseItem.value.expense_type, __)
)

const mileageLine = computed(() =>
	mileageExplainer(expenseItem.value.distance_km, mileageRate.value, (money) =>
		formatCurrency(money, props.expenseClaim.currency)
	)
)

// mileage: the amount follows the distance (owner, 14 Oct 2026); the server
// prices the line again on save, so this is what the employee sees, not the rule
watch(
	() => [expenseItem.value.distance_km, mileageRate.value],
	([km, rate]) => {
		if (rate > 0) expenseItem.value.amount = mileageAmount(km, rate)
	}
)

// child table form scripts
watch(
	() => expenseItem.value.expense_type,
	(value) => {
		// The GL account is its own read-only row now (owner, 29 Oct 2026), not
		// "GL: ..." copied into the Description for staff to edit.
		expenseItem.value[GL_FIELD] = claimTypesByID[value]?.gl_account || null

		// fill only: a cost tag picked on the line is the employee's choice
		expenseItem.value.cost_center ||= props.expenseClaim.cost_center
	}
)

watch(
	() => expenseItem.value.amount,
	(value) => {
		if (!isFirstRender.value) {
			// parseFloat("") is NaN, which persisted as a wrong null on submit
			// when the amount was cleared; fall back to 0.
			expenseItem.value.sanctioned_amount = parseFloat(value) || 0
		} else {
			isFirstRender.value = false
		}
	}
)
</script>
