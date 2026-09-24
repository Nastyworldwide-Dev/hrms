<template>
	<!-- Header -->
	<div class="flex flex-row justify-between items-center mt-2 pb-2 border-b-2 border-divider">
		<h2 class="g-eyebrow">{{ __("Expenses") }}</h2>
		<div class="flex flex-row gap-3 items-center">
			<span class="text-base font-extrabold text-inkbase">
				{{ formatCurrency(expenseClaim.total_claimed_amount, expenseClaim.currency) }}
			</span>
			<GIconButton
				v-if="!isReadOnly"
				id="add-expense-modal"
				:label="__('Add an expense')"
				@click="openModal()"
			>
				<Plus class="w-4" />
			</GIconButton>
		</div>
	</div>

	<!-- Table -->
	<!-- §6.3: an expense figure is a number someone disputes with their
	     manager, so it sits on an opaque surface — never glass, never a
	     translucent track. -->
	<div v-if="expenseClaim.expenses" class="g-lineitems flex flex-col overflow-auto">
		<div
			class="g-lineitems__row flex flex-row py-3 px-3 items-center justify-between cursor-pointer"
			v-for="(item, idx) in expenseClaim.expenses"
			:key="idx"
			role="button"
			tabindex="0"
			@click="openModal(item, idx)"
			@keydown.enter.prevent="openModal(item, idx)"
			@keydown.space.prevent="openModal(item, idx)"
		>
			<div class="flex flex-col w-full justify-center gap-2.5">
				<div class="flex flex-row items-center justify-between">
					<div class="flex flex-row items-start gap-3 grow">
						<div class="flex flex-col items-start gap-1.5">
							<div class="text-button-label font-semibold text-inkbase">
								{{ __(item.expense_type) }}
							</div>
							<div class="text-xs font-normal text-ink-600">
								<span>
									{{
										__("{0}: {1}", [
											__("Approved"),
											formatCurrency(item.sanctioned_amount || 0, expenseClaim.currency),
										])
									}}
								</span>
								<span class="whitespace-pre"> &middot; </span>
								<span class="whitespace-nowrap" v-if="item.expense_date">
									{{ dayjs(item.expense_date).format("D MMM") }}
								</span>
							</div>
						</div>
					</div>
					<div class="flex flex-row justify-end items-center gap-2">
						<span class="text-inkbase font-semibold text-base">
							{{ formatCurrency(item.amount, expenseClaim.currency) }}
						</span>
						<ChevronRight class="h-5 w-5 text-ink-500" />
					</div>
				</div>
			</div>
		</div>
	</div>
	<GEmptyState
		v-else
		:title="__('No expenses added')"
		:body="__('Add each item you paid for with the + above')"
	/>

	<GModal :is-open="isModalOpen" :title="modalTitle" @did-dismiss="resetSelectedItem()">
			<!-- Add Expense Action Sheet -->
			<div class="bg-ground w-full flex flex-col pb-5">
				<div class="w-full flex flex-col items-center justify-center gap-5 p-4 max-h-[80vh]">
					<div class="flex flex-col w-full space-y-4 overflow-y-auto expense-fields">
						<FormField
							v-for="field in expenseFields"
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
import { ChevronRight, Plus } from "lucide-vue-next"
import { createResource } from "frappe-ui"
import GButton from "@/components/glass/GButton.vue"
import GIconButton from "@/components/glass/GIconButton.vue"
import { computed, ref, watch, inject } from "vue"

import FormField from "@/components/FormField.vue"
import GEmptyState from "@/components/glass/GEmptyState.vue"
import GModal from "@/components/glass/GModal.vue"

import { claimTypesByID, claimTypesResource } from "@/data/claims"
import { formatCurrency } from "@/utils/formatters"
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
		// alpha.6: the employee enters what they paid. "Sanctioned amount" is
		// the approver's number (it follows the amount, watch below), and cost
		// center / department / location are accounting tags the claim stamps
		// from the company (Form.vue); none is a question for the employee.
		const excludeFields = [
			"description_sb",
			"amounts_sb",
			"base_amount",
			"base_sanctioned_amount",
			"sanctioned_amount",
			"cost_center",
			"department",
			"location",
			"project",
			"accounting_dimensions_section",
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

<style scoped>
.expense-fields :deep(input:not([type="checkbox"]):not([type="radio"])),
.expense-fields :deep(textarea),
.expense-fields :deep(select) {
	background-color: var(--g-glass-fill-fallback);
	border: 1px solid var(--g-hair);
	border-radius: 0;
	font-size: 14px;
	color: var(--g-ink);
}
.expense-fields :deep(input:not([type="checkbox"]):not([type="radio"]):focus),
.expense-fields :deep(textarea:focus),
.expense-fields :deep(select:focus) {
	border-color: var(--g-accent-ink);
	box-shadow: none;
	outline: none;
}
</style>
