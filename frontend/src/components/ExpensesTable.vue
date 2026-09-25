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
		<GEmptyState
			v-else
			:title="__('No expenses added')"
			:body="__('Add each item you paid for with the + above')"
		/>
		<p v-if="expenseClaim.expenses?.length" class="g-form-footer">
			{{ __("Total {0}", [formatCurrency(expenseClaim.total_claimed_amount, expenseClaim.currency)]) }}
		</p>
	</section>

	<GModal :is-open="isModalOpen" :title="modalTitle" @did-dismiss="resetSelectedItem()">
		<!-- Add Expense Action Sheet -->
		<div class="w-full flex flex-col pb-5">
			<div class="w-full flex flex-col items-center justify-center gap-5 p-4 max-h-[80vh]">
				<div class="w-full overflow-y-auto expense-fields">
					<section
						v-for="group in groupFields(expenseFields)"
						:key="group.key"
						class="g-form-section mb-4"
					>
						<h2 v-if="group.label" class="g-form-section__title">
							{{ sentenceCase(__(group.label, null, "Expense Claim Detail")) }}
						</h2>
						<div v-for="(segment, s) in group.segments" :key="s" class="g-form-group">
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
								v-model="expenseItem[field.fieldname]"
							/>
						</div>
					</section>
				</div>

				<div v-if="!isReadOnly" class="flex w-full flex-row items-center justify-between gap-3">
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
						@click="updateExpenseItem()"
					/>
				</div>
			</div>
		</div>
	</GModal>
</template>

<script setup>
import { Plus } from "lucide-vue-next"
import { createResource } from "frappe-ui"
import GButton from "@/components/glass/GButton.vue"
import GIconButton from "@/components/glass/GIconButton.vue"
import { computed, ref, watch, inject } from "vue"

import FormField from "@/components/FormField.vue"
import GEmptyState from "@/components/glass/GEmptyState.vue"
import GListPanel from "@/components/glass/GListPanel.vue"
import GListRow from "@/components/glass/GListRow.vue"
import GModal from "@/components/glass/GModal.vue"

import { claimTypesByID, claimTypesResource } from "@/data/claims"
import { formatCurrency } from "@/utils/formatters"
import { groupFields } from "@/utils/formGroups"
import { sentenceCase } from "@/utils/sentenceCase"
import { withCostTagFields } from "@/utils/expenseCostTags"

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
const isFirstRender = ref(false)

const openModal = async (item, idx) => {
	if (item) {
		expenseItem.value = { ...item }
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
	if (editingIdx.value === null) {
		emit("add-expense-item", expenseItem.value)
	} else {
		emit("update-expense-item", expenseItem.value, editingIdx.value)
	}
	resetSelectedItem()
}

//: "Approved RM 12.50 · 21 Sep" — what came back and when, under the type.
function itemLine(item) {
	const approved = __("{0}: {1}", [__("Approved"), formatCurrency(item.sanctioned_amount || 0, props.expenseClaim.currency)])
	const day = item.expense_date ? dayjs(item.expense_date).format("D MMM") : ""
	return [approved, day].filter(Boolean).join(" · ")
}

function resetSelectedItem() {
	isFirstRender.value = false
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

const expenseFields = computed(() =>
	withCostTagFields(
		(expensesTableFields.data || []).map((field) =>
			field.fieldname === "expense_type"
				? { ...field, documentList: expenseTypeOptions.value }
				: field
		),
		costTags.data
	)
)

const expenseClaimRef = computed(() => props.expenseClaim)
useCurrencyConversion(expensesTableFields, expenseClaimRef, ["amount", "sanctioned_amount"])

const modalTitle = computed(() => {
	if (props.isReadOnly) return __("Expense item")

	return editingIdx.value === null ? __("New expense item") : __("Edit expense item")
})

const addButtonDisabled = computed(() => {
	return expensesTableFields.data?.some((field) => {
		if (field.reqd && !expenseItem.value[field.fieldname]) {
			return true
		}
	})
})

// child table form scripts
watch(
	() => expenseItem.value.expense_type,
	(value) => {
		if (!expenseItem.value.description) {
			expenseItem.value.description = claimTypesByID[value]?.description
		}

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
