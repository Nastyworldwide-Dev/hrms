from pypika.terms import ValueWrapper

import frappe


def execute():
	employee_holiday_details = get_employee_holiday_details()
	company_holiday_details = get_company_holiday_details()
	if not (employee_holiday_details or company_holiday_details):
		return

	for entity in employee_holiday_details + company_holiday_details:
		try:
			create_holiday_list_assignment(entity)
		except Exception as e:
			frappe.log_error(e)


def create_holiday_list_assignment(entity_details):
	# Filter on columns the assignment HAS. The row from the queries below also
	# carries `to_date` and `company`; an unknown column makes frappe.db.exists
	# swallow the error and answer None, so every post-sync run re-inserted every
	# row and logged a DuplicateAssignment per employee (21 Sep 2026, G-F4).
	existing = {
		"assigned_to": entity_details.get("assigned_to"),
		"from_date": entity_details.get("from_date"),
		"docstatus": 1,
	}
	if not frappe.db.exists("Holiday List Assignment", existing):
		hla = frappe.new_doc("Holiday List Assignment")
		hla.update(entity_details)
		hla.save()
		hla.submit()


def get_employee_holiday_details():
	employee = frappe.qb.DocType("Employee")
	holiday_list = frappe.qb.DocType("Holiday List")
	applicable_for = ValueWrapper("Employee", "applicable_for")
	employee_holiday_details = (
		frappe.qb.from_(employee)
		.inner_join(holiday_list)
		.on(employee.holiday_list == holiday_list.name)
		.select(
			(employee.name).as_("assigned_to"),
			employee.holiday_list,
			holiday_list.from_date,
			holiday_list.to_date,
			employee.company,
			applicable_for,
		)
		.where(employee.status == "Active")
	).run(as_dict=True)

	return employee_holiday_details


def get_company_holiday_details():
	company = frappe.qb.DocType("Company")
	holiday_list = frappe.qb.DocType("Holiday List")
	applicable_for = ValueWrapper("Company", "applicable_for")
	company_holiday_details = (
		frappe.qb.from_(company)
		.inner_join(holiday_list)
		.on(company.default_holiday_list == holiday_list.name)
		.select(
			(company.name).as_("assigned_to"),
			(company.default_holiday_list).as_("holiday_list"),
			holiday_list.from_date,
			holiday_list.to_date,
			applicable_for,
		)
	).run(as_dict=True)

	return company_holiday_details
