<template>
	<GPage>
		<ion-content :fullscreen="true">
			<FormView
				v-if="formFields.data"
				doctype="Expense Claim"
				:noun="__('expense claim')"
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
import { approverOptions } from "@/utils/approverOptions"
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
	// reqd, but it lives in the Desk form's Accounting tab — past `taxes`, the
	// last field of the one tab rendered here — so no FormField ever mounts
	// for it and a mount-time `field.default` never ran. Seed the model.
	posting_date: today,
})

const companyCurrency = computed(() => getCompanyCurrency(expenseClaim.value.company))

// get form fields
const formFields = createResource({
	url: "hrms.api.get_doctype_fields",
	params: { doctype: "Expense Claim" },
	transform(data) {
		return getFilteredFields(data)
	},
	onSuccess(_data) {
		expenseApproverDetails.reload()
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

// The claim is filed in the COMPANY currency at rate 1 (the Currency / Exchange
// Rate inputs are hidden). Currency must come from the company, never the
// employee's salary currency: a USD-salaried employee filing against an MYR
// company would otherwise store currency=USD at exchange_rate=1, and the backend
// (set_base_fields_amount) would treat 1 USD as 1 MYR — wrong base totals. The
// company-currencies resource may resolve after this form mounts, so set it
// reactively. Existing claims (props.id) keep whatever currency they were saved
// with; only new claims are stamped here.
watch(
	() => [companyCurrency.value, expenseClaim.value.company],
	() => {
		if (props.id) return
		if (companyCurrency.value) expenseClaim.value.currency = companyCurrency.value
	},
	{ immediate: true }
)

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
			expense.cost_center ||= expenseClaim.value.cost_center
		})
	}
)

// helper functions
//: The fields this screen asks for. An ALLOWLIST, replacing an
//: `excludeFields` blacklist that had grown to eighteen entries chasing the
//: same problem: a blacklist hides what it knows and SHOWS what it does not,
//: so every schema change is a potential leak.
//:
//: Read against the running site, the old list was letting through
//: `gain_loss_account`, `total_exchange_gain_loss`, `delivery_trip`,
//: `vehicle_log`, `amended_from`, `bank_or_cash_account`, `location`,
//: `branch`, and the Accounting and Dashboard tabs — 36 of the doctype's 61
//: fields reached an employee filing a receipt.
//: No posting_date (owner ruling Q4, 24 Sep 2026): it is the claim's
//: accounting date, seeded with today on the model below; each expense line
//: carries its own date. No total fields either: the Expenses header already
//: shows the running total, and three read-only boxes repeating it ("12.5",
//: "12.5", "12.5" under "Totals") were noise. calculateTotals() still sets
//: them on the model, so the server receives them as before.
const FIELDS = ["expenses", "expense_approver"]

//: Shown only when READING an existing claim, as the blacklist also did: on a
//: new one these come from the session or are not yet meaningful.
const FIELDS_ON_EXISTING = [
	"employee",
	"employee_name",
	"department",
	"company",
	"status",
	"total_amount_reimbursed",
]

//: Layout by KIND, not by name — `column_break_imlz` and `column_break_quih`
//: are generated and change whenever the doctype is reordered in Desk.
//: Tab Break is NOT here: this form is one flow, and the doctype's tabs
//: (Accounting, More Info, Dashboard) are the ERP's organisation, not the
//: employee's.
const LAYOUT = ["Section Break", "Column Break"]

function getFilteredFields(fields) {
	const wanted = props.id ? [...FIELDS, ...FIELDS_ON_EXISTING] : FIELDS
	return fields.filter(
		(field) => wanted.includes(field.fieldname) || LAYOUT.includes(field.fieldtype)
	)
}

function setExpenseApprover(data) {
	const expense_approver = formFields.data?.find((field) => field.fieldname === "expense_approver")
	expense_approver.reqd = data?.is_mandatory
	expense_approver.documentList = approverOptions(data?.department_approvers)

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
	// fill the company cost center into rows that carry no cost tag of their own
	expenseClaim?.value?.expenses?.forEach((expense) => {
		expense.cost_center ||= expenseClaim.value.cost_center
	})
}
</script>
