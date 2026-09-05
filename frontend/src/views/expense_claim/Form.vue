<template>
	<GPage>
		<ion-content :fullscreen="true">
			<FormView
				v-if="formFields.data"
				doctype="Expense Claim"
				v-model="expenseClaim"
				:isSubmittable="true"
				:fields="formFields.data"
				:id="props.id"
				:tabbedView="true"
				:tabs="tabs"
				:showAttachmentView="true"
				@validateForm="validateForm"
				:showDownloadPDFButton="true"
				@formReloaded="onFormReloaded"
			>
				<!-- Child Tables -->
				<template #expenses="{ isFormReadOnly }">
					<ExpensesTable
						v-model:expenseClaim="expenseClaim"
						:isReadOnly="isReadOnly || isFormReadOnly"
						@addExpenseItem="addExpenseItem"
						@updateExpenseItem="updateExpenseItem"
						@deleteExpenseItem="deleteExpenseItem"
					/>
				</template>

				<template #taxes="{ isFormReadOnly }">
					<ExpenseTaxesTable
						v-model:expenseClaim="expenseClaim"
						:isReadOnly="isReadOnly || isFormReadOnly"
						@addExpenseTax="addExpenseTax"
						@updateExpenseTax="updateExpenseTax"
						@deleteExpenseTax="deleteExpenseTax"
					/>
				</template>
			</FormView>
			<ResourceError :resource="formFields" back what="the expense claim form" />
		</ion-content>
	</GPage>
</template>

<script setup>
import GPage from "@/components/glass/GPage.vue"
import { IonContent } from "@ionic/vue"
import { createResource } from "frappe-ui"
import { computed, ref, watch, inject } from "vue"

import FormView from "@/components/FormView.vue"
import ExpensesTable from "@/components/ExpensesTable.vue"
import ExpenseTaxesTable from "@/components/ExpenseTaxesTable.vue"
import { getCompanyCurrency } from "@/data/currencies"

const dayjs = inject("$dayjs")

const today = dayjs().format("YYYY-MM-DD")
const isReadOnly = ref(false)

const sessionEmployee = inject("$employee")
const currEmployee = ref(sessionEmployee.data.name)
const employeeCompany = ref(sessionEmployee.data.company)

const props = defineProps({
	id: {
		type: String,
		required: false,
	},
})

// Employee flow only: approver, expense items, taxes, attachments. The Advances
// and Totals tabs and the Currency/Exchange Rate section are ERP concerns not
// appropriate here — the claim is filed in the company currency at rate 1, and
// the required backend fields (currency, exchange_rate, cost_center,
// payable_account) are populated from company defaults below.
const tabs = [{ name: "Expenses", lastField: "taxes" }]

// object to store form data
const expenseClaim = ref({
	employee: currEmployee,
	company: employeeCompany,
	doctype: "Expense Claim",
	// reqd on the doctype; defaulted so a hidden field never blocks submit.
	exchange_rate: 1,
})

const companyCurrency = computed(() => getCompanyCurrency(expenseClaim.value.company))

// get form fields
const formFields = createResource({
	url: "hrms.api.get_doctype_fields",
	params: { doctype: "Expense Claim" },
	transform(data) {
		let fields = getFilteredFields(data)

		return fields.map((field) => {
			if (field.fieldname === "posting_date") field.default = today
			return field
		})
	},
	onSuccess(_data) {
		expenseApproverDetails.reload()
		if (!expenseClaim.value.currency) {
			employeeCurrency.reload()
		}
		companyDetails.reload()
	},
})
formFields.reload()

// resources & helper functions
function onFormReloaded() {
	// Advances are not managed in the employee flow; nothing to reload here.
}

const expenseApproverDetails = createResource({
	url: "hrms.api.get_expense_approval_details",
	params: { employee: currEmployee.value },
	onSuccess(data) {
		setExpenseApprover(data)
	},
})

// Through the fenced endpoint, never frappe.client.get_value on Employee:
// the raw read needs Desk permission on the doctype and a bare-Employee
// user has none — same failure family as the Department toast.
const employeeCurrency = createResource({
	url: "hrms.api.get_salary_currency",
	makeParams() {
		return { employee: currEmployee.value }
	},
	onSuccess(data) {
		// The claim is filed in a single currency at rate 1; fall back to the
		// company currency when the employee has no salary currency, so the
		// reqd currency field is always populated for the backend.
		expenseClaim.value.currency = data || companyCurrency.value
	},
})

const companyDetails = createResource({
	url: "hrms.api.get_company_cost_center_and_expense_account",
	params: { company: expenseClaim.value.company },
	onSuccess(data) {
		expenseClaim.value.cost_center = data?.cost_center
		expenseClaim.value.payable_account = data?.default_expense_claim_payable_account
	},
})

// form scripts
watch(
	() => expenseClaim.value.employee,
	(employee_id) => {
		if (props.id && employee_id !== currEmployee.value) {
			// if employee is not the current user, set form as read only
			setFormReadOnly()
		}
		currEmployee.value = employee_id
		expenseApproverDetails.fetch({ employee: currEmployee.value })
		employeeCurrency.fetch()
	}
)

watch(
	() => expenseClaim.value.company,
	(company) => {
		employeeCompany.value = company
		companyDetails.fetch({ company: employeeCompany.value })
	}
)

watch(
	() => expenseClaim.value.cost_center,
	() => {
		expenseClaim?.value?.expenses?.forEach((expense) => {
			expense.cost_center = expenseClaim.value.cost_center
		})
	}
)

// helper functions
function getFilteredFields(fields) {
	// reduce noise from the form view by excluding unnecessary fields
	// eg: employee and other details can be fetched from the session user
	// Currency section + Exchange Rate are ERP concerns removed from the
	// employee flow; they sit before the expense table so they must be excluded
	// explicitly (their values are set to the company currency at rate 1 above).
	const excludeFields = [
		"naming_series",
		"task",
		"taxes_and_charges_sb",
		"advance_payments_sb",
		"currency_section",
		"currency",
		"column_break_imlz",
		"exchange_rate",
		// Backend plumbing, not employee choices: cost_center and payable_account are
		// filled from the company default (companyDetails, below) and stamped onto each
		// row — showing them as pickers an Employee can't even search (Account / Cost
		// Center masters) was pure confusion. project isn't used on employee claims.
		// The values are still set on the object; only the inputs are hidden.
		"cost_center",
		"payable_account",
		"project",
	]
	const extraFields = [
		"employee",
		"employee_name",
		"department",
		"company",
		"remark",
		"is_paid",
		"mode_of_payment",
		"clearance_date",
		"approval_status",
	]

	if (!props.id) excludeFields.push(...extraFields)

	return fields.filter((field) => {
		if (excludeFields.includes(field.fieldname)) return false

		if (field.fieldname?.startsWith("base_")) return false
		return true
	})
}

function setExpenseApprover(data) {
	const expense_approver = formFields.data?.find((field) => field.fieldname === "expense_approver")
	expense_approver.reqd = data?.is_mandatory
	expense_approver.documentList = data?.department_approvers.map((approver) => ({
		label: approver.full_name ? `${approver.name} : ${approver.full_name}` : approver.name,
		value: approver.name,
	}))

	expenseClaim.value.expense_approver = data?.expense_approver
	expenseClaim.value.expense_approver_name = data?.expense_approver_name
}

function addExpenseItem(item) {
	if (!expenseClaim.value.expenses) expenseClaim.value.expenses = []
	expenseClaim.value.expenses.push(item)
	calculateTotals()
	calculateTaxes()
}

function updateExpenseItem(item, idx) {
	expenseClaim.value.expenses[idx] = item
	calculateTotals()
	calculateTaxes()
}

function deleteExpenseItem(idx) {
	expenseClaim.value.expenses.splice(idx, 1)
	calculateTotals()
	calculateTaxes()
}

function addExpenseTax(item) {
	if (!expenseClaim.value.taxes) expenseClaim.value.taxes = []
	expenseClaim.value.taxes.push(item)
	calculateTaxes()
}

function updateExpenseTax(item, idx) {
	expenseClaim.value.taxes[idx] = item
	calculateTaxes()
}

function deleteExpenseTax(idx) {
	expenseClaim.value.taxes.splice(idx, 1)
	calculateTaxes()
}

function calculateTotals() {
	let total_claimed_amount = 0
	let total_sanctioned_amount = 0

	expenseClaim.value?.expenses?.forEach((item) => {
		total_claimed_amount += parseFloat(item.amount) || 0
		total_sanctioned_amount += parseFloat(item.sanctioned_amount) || 0
	})

	expenseClaim.value.total_claimed_amount = total_claimed_amount
	expenseClaim.value.total_sanctioned_amount = total_sanctioned_amount
	calculateGrandTotal()
}

function calculateTaxes() {
	let total_taxes_and_charges = 0

	expenseClaim.value?.taxes?.forEach((item) => {
		if (item.rate) {
			item.tax_amount =
				(parseFloat(expenseClaim.value.total_sanctioned_amount) || 0) *
				(parseFloat(item.rate / 100) || 0)
		}

		item.total =
			(parseFloat(item.tax_amount) || 0) +
			(parseFloat(expenseClaim.value.total_sanctioned_amount) || 0)
		total_taxes_and_charges += parseFloat(item.tax_amount) || 0
	})
	expenseClaim.value.total_taxes_and_charges = total_taxes_and_charges
	calculateGrandTotal()
}

function calculateGrandTotal() {
	expenseClaim.value.grand_total =
		parseFloat(expenseClaim.value.total_sanctioned_amount || 0) +
		parseFloat(expenseClaim.value.total_taxes_and_charges || 0) -
		parseFloat(expenseClaim.value.total_advance_amount || 0)
}

function setFormReadOnly() {
	if (props.id && expenseClaim.value.expense_approver !== currEmployee.value) return
	formFields.data.map((field) => (field.read_only = true))
	isReadOnly.value = true
}

function validateForm() {
	// stamp the cost center (from company defaults) onto each expense row
	expenseClaim?.value?.expenses?.forEach((expense) => {
		expense.cost_center = expenseClaim.value.cost_center
	})
}
</script>
