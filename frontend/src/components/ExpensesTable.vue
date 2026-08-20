<template>
	<!-- Header -->
	<div class="flex flex-row justify-between items-center mt-2 pb-2 border-b-2 border-divider">
		<h2 class="text-eyebrow uppercase text-accent-ink">{{ __("Expenses") }} </h2>
		<div class="flex flex-row gap-3 items-center">
			<span class="text-base font-extrabold text-inkbase">
				{{ formatCurrency(expenseClaim.total_claimed_amount, expenseClaim.currency) }}
			</span>
			<Button
				v-if="!isReadOnly"
				id="add-expense-modal"
				class="text-sm !border !border-divider !bg-transparent"
				icon="plus"
				variant="subtle"
				@click="openModal()"
			/>
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
			@click="openModal(item, idx)"
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
											__("Sanctioned"),
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
						<FeatherIcon name="chevron-right" class="h-5 w-5 text-ink-500" />
					</div>
				</div>
			</div>
		</div>
	</div>
	<EmptyState v-else :message="__('No expenses added')" :isTableField="true" />

	<CustomIonModal :isOpen="isModalOpen" @didDismiss="resetSelectedItem()">
		<template #actionSheet>
			<!-- Add Expense Action Sheet -->
			<div
				class="bg-ground w-full flex flex-col pb-5"
			>
				<div class="w-full pt-6 pb-4 px-4 border-b border-divider flex flex-col gap-1">
					<div class="text-eyebrow uppercase text-accent-ink">{{ __("Expense") }}</div>
					<span class="text-inkbase font-extrabold text-stat-number leading-tight">
						{{ modalTitle }}
					</span>
				</div>
				<div class="w-full flex flex-col items-center justify-center gap-5 p-4 max-h-[80vh]">
					<div class="flex flex-col w-full space-y-4 overflow-y-auto expense-fields">
						<FormField
							v-for="field in expensesTableFields.data"
							:key="field.fieldname"
							class="w-full"
							:label="__(field.label, null, 'Expense Claim Detail')"
							:fieldtype="field.fieldtype"
							:fieldname="field.fieldname"
							:options="field.options"
							:hidden="field.hidden"
							:reqd="field.reqd"
							:default="field.default"
							:readOnly="field.read_only || isReadOnly"
							v-model="expenseItem[field.fieldname]"
						/>
					</div>

					<div
						v-if="!isReadOnly"
						class="flex w-full flex-row items-center justify-between gap-3"
					>
						<Button
							v-if="editingIdx !== null"
							class="!border !border-red-600 !text-red-600 !bg-transparent py-5 text-sm"
							variant="outline"
							theme="red"
							@click="deleteExpenseItem()"
						>
							<template #prefix>
								<FeatherIcon name="trash" class="w-4" />
							</template>
							{{ __("Delete") }}
						</Button>
						<Button
							variant="solid"
							class="w-full py-5 text-sm !bg-accent hover:!bg-accent-600 !text-ground !border-none disabled:opacity-60"
							@click="updateExpenseItem()"
							:disabled="addButtonDisabled"
						>
							<template #prefix>
								<FeatherIcon
									:name="editingIdx === null ? 'plus' : 'check'"
									class="w-4"
								/>
							</template>
							{{ editingIdx === null ? __("Add Expense") : __("Update Expense") }}
						</Button>
					</div>
				</div>
			</div>
		</template>
	</CustomIonModal>
</template>

<script setup>
import { FeatherIcon, createResource } from "frappe-ui"
import { computed, ref, watch, inject } from "vue"

import FormField from "@/components/FormField.vue"
import EmptyState from "@/components/EmptyState.vue"
import CustomIonModal from "@/components/CustomIonModal.vue"

import { claimTypesByID } from "@/data/claims"
import { formatCurrency } from "@/utils/formatters"

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
const emit = defineEmits([
	"add-expense-item",
	"update-expense-item",
	"delete-expense-item",
])
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
		const excludeFields = ["description_sb", "amounts_sb", "base_amount", "base_sanctioned_amount"]
		return data.filter((field) => !excludeFields.includes(field.fieldname))
	},
})
expensesTableFields.reload()

const expenseClaimRef = computed(() => props.expenseClaim)
useCurrencyConversion(
	expensesTableFields,
	expenseClaimRef,
	["amount", "sanctioned_amount"]
)

const modalTitle = computed(() => {
	if (props.isReadOnly) return __("Expense Item")

	return editingIdx.value === null ? __("New Expense Item") : __("Edit Expense Item")
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

		expenseItem.value.cost_center = props.expenseClaim.cost_center
	}
)

watch(
	() => expenseItem.value.amount,
	(value) => {
		if (!isFirstRender.value) {
			expenseItem.value.sanctioned_amount = parseFloat(value)
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
