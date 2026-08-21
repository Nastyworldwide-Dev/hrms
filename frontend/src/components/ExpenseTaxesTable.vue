<template>
	<template v-if="expenseClaim.expenses">
		<div class="flex flex-row justify-between items-center pt-4 pb-2 border-b-2 border-divider">
			<h2 class="g-eyebrow">{{ __("Taxes & Charges") }} </h2>
			<div class="flex flex-row gap-3 items-center">
				<span class="text-base font-extrabold text-inkbase">
					{{ formatCurrency(expenseClaim.total_taxes_and_charges, expenseClaim.currency) }}
				</span>
				<Button
					v-if="!isReadOnly"
					id="add-taxes-modal"
					class="text-sm !border !border-divider !bg-transparent"
					icon="plus"
					variant="subtle"
					@click="openModal()"
				/>
			</div>
		</div>

		<div
			v-if="expenseClaim.taxes?.length"
			class="g-lineitems flex flex-col overflow-auto"
		>
			<div
				class="g-lineitems__row flex flex-row py-3 px-3 items-center justify-between cursor-pointer"
				v-for="(item, idx) in expenseClaim.taxes"
				:key="item.name"
				@click="openModal(item, idx)"
			>
				<div class="flex flex-col w-full justify-center gap-2.5">
					<div class="flex flex-row items-center justify-between">
						<div class="flex flex-row items-start gap-3 grow">
							<div class="flex flex-col items-start gap-1.5">
								<div class="text-button-label font-semibold text-inkbase">
									{{ item.account_head }}
								</div>
								<div class="text-xs font-normal text-ink-600">
									<span> Rate: {{ formatCurrency(item.rate, expenseClaim.currency) }} </span>
									<span class="whitespace-pre"> &middot; </span>
									<span class="whitespace-nowrap">
										Amount: {{ formatCurrency(item.tax_amount, expenseClaim.currency) }}
									</span>
								</div>
							</div>
						</div>
						<div class="flex flex-row justify-end items-center gap-2">
							<span class="text-inkbase font-semibold text-base">
								{{ formatCurrency(item.total, expenseClaim.currency) }}
							</span>
							<FeatherIcon name="chevron-right" class="h-5 w-5 text-ink-500" />
						</div>
					</div>
				</div>
			</div>
		</div>
		<GEmptyState v-else :title="__('No taxes added')" :body="__('Add one with the + above if this claim carries tax')" />

		<CustomIonModal :isOpen="isModalOpen" @didDismiss="resetSelectedItem()">
			<template #actionSheet>
				<!-- Add Expense Tax Action Sheet -->
				<div
					class="bg-ground w-full flex flex-col pb-5"
				>
					<div class="w-full pt-6 pb-4 px-4 border-b border-divider flex flex-col gap-1">
						<div class="g-eyebrow">{{ __("Tax") }}</div>
						<span class="text-inkbase font-extrabold text-stat-number leading-tight">
							{{ modalTitle }}
						</span>
					</div>
					<div
						class="w-full flex flex-col items-center justify-center gap-5 p-4"
					>
						<div class="flex flex-col w-full space-y-4 expense-fields">
							<FormField
								v-for="field in taxesTableFields.data"
								:key="field.fieldname"
								class="w-full"
								:label="__(field.label, null, 'Expense Claim Detail')"
								:fieldtype="field.fieldtype"
								:fieldname="field.fieldname"
								:options="field.options"
								:linkFilters="field.linkFilters"
								:hidden="field.hidden"
								:reqd="field.reqd"
								:readOnly="field.read_only || isReadOnly"
								:default="field.default"
								v-model="expenseTax[field.fieldname]"
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
								@click="deleteExpenseTax()"
							>
								<template #prefix>
									<FeatherIcon name="trash" class="w-4" />
								</template>
								{{ __("Delete") }}
							</Button>
							<Button
								variant="solid"
								class="w-full py-5 text-sm !bg-accent-ink hover:!bg-accent-600 !text-ground !border-none disabled:opacity-60"
								@click="updateExpenseTax()"
								:disabled="addButtonDisabled"
							>
								<template #prefix>
									<FeatherIcon
										:name="editingIdx === null ? 'plus' : 'check'"
										class="w-4"
									/>
								</template>
								{{ editingIdx === null ? __("Add Tax") : __("Update Tax") }}
							</Button>
						</div>
					</div>
				</div>
			</template>
		</CustomIonModal>
	</template>
</template>

<script setup>
import { FeatherIcon, createResource } from "frappe-ui"
import { computed, ref, watch, inject } from "vue"

import FormField from "@/components/FormField.vue"
import GEmptyState from "@/components/glass/GEmptyState.vue"
import CustomIonModal from "@/components/CustomIonModal.vue"

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
	"add-expense-tax",
	"update-expense-tax",
	"delete-expense-tax",
])
const __ = inject("$translate")
const expenseTax = ref({})
const editingIdx = ref(null)

const isModalOpen = ref(false)
const openModal = async (item, idx) => {
	if (item) {
		expenseTax.value = { ...item }
		editingIdx.value = idx
	}
	isModalOpen.value = true
}

const deleteExpenseTax = () => {
	emit("delete-expense-tax", editingIdx.value)
	resetSelectedItem()
}

const updateExpenseTax = () => {
	if (editingIdx.value === null) {
		emit("add-expense-tax", expenseTax.value)
	} else {
		emit("update-expense-tax", expenseTax.value, editingIdx.value)
	}
	resetSelectedItem()
}

function resetSelectedItem() {
	isModalOpen.value = false
	expenseTax.value = {}
	editingIdx.value = null
}

const taxesTableFields = createResource({
	url: "hrms.api.get_doctype_fields",
	params: { doctype: "Expense Taxes and Charges" },
	transform(data) {
		const excludeFields = ["description_sb"]
		return data
			.map((field) => {
				if (field.fieldname === "account_head") {
					field.linkFilters = {
						company: props.expenseClaim.company,
						account_type: [
							"in",
							[
								"Tax",
								"Chargeable",
								"Income Account",
								"Expenses Included In Valuation",
							],
						],
					}
				}
				return field
			})
			.filter((field) => !excludeFields.includes(field.fieldname))
	},
})
taxesTableFields.reload()

const expenseClaimRef = computed(() => props.expenseClaim)
useCurrencyConversion(
	taxesTableFields,
	expenseClaimRef,
	["tax_amount", "total"]
)

const modalTitle = computed(() => {
	if (props.isReadOnly) return __("Expense Tax")

	return editingIdx.value === null ? __("New Expense Tax") : __("Edit Expense Tax")
})

const addButtonDisabled = computed(() => {
	return taxesTableFields.data?.some((field) => {
		if (field.reqd && !expenseTax.value[field.fieldname]) {
			return true
		}
	})
})

// child table scripts
watch(
	() => expenseTax.value.account_head,
	(value) => {
		// set description from account head
		expenseTax.value.description = value?.split(" - ").slice(0, -1).join(" - ")
	}
)

watch(
	() => expenseTax.value.rate,
	(newVal, oldVal) => {
		if (editingIdx.value && newVal && !oldVal) return

		expenseTax.value.tax_amount =
			parseFloat(props.expenseClaim.total_sanctioned_amount) *
			(parseFloat(newVal) / 100)
		calculateTotalTax()
	}
)

watch(
	() => expenseTax.value.tax_amount,
	(_value) => {
		calculateTotalTax()
	}
)

function calculateTotalTax() {
	expenseTax.value.total =
		parseFloat(props.expenseClaim.total_sanctioned_amount) +
		parseFloat(expenseTax.value.tax_amount)
}
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
