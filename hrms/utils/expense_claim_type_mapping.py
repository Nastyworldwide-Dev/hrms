"""HR's expense claim types, each wired to its GL account in every company.

HR handed over the mapping on 9 September 2026 (claim item → "GL in ERP").
Eleven types times fifteen companies is 165 account rows nobody should key by
hand, and a type without a row for the claimant's company is refused at save.
So the mapping lives here, `apply_expense_claim_type_mapping` is idempotent —
creates a missing type, adds a missing account row wherever the named GL
account exists for that company, touches nothing that is already there — and
it runs on deploy (patch) and again at the end of every "Pull → GL Accounts"
run, when the accounts it needs have just arrived.

The account is found by its account NAME within the company (the ERP may
number its accounts, so the document name is not composed here).
"""

import logging

import frappe

logger = logging.getLogger(__name__)

#: Claim type (exactly as HR wrote it) -> account name in the ERP's chart.
MAPPING = {
	"Car Rental (CAR RENTAL)": "Travel Expenses",
	"Flight / Public Transport (FLIGHT/PT)": "Travel Expenses",
	"General & Administrative (G&A)": "General & Administrative",
	"Gym & Wellness Subsidy (GYM&WS)": "Employee Benefits",
	"Lodging / Hotel (LODGING/HOTEL)": "Travel Expenses",
	"Meals & Entertainment (M&E)": "Employee Meals & Entertainment",
	"Mileage (CAR) (MILEAGE CAR)": "Fuel/Mileage Expenses",
	"Mileage (Motorcycle) (MILEAGE MOTORCYCLE)": "Fuel/Mileage Expenses",
	"Parking & Toll (PARKING&TOLL)": "Parking & Toll",
	"Petrol (PETROL)": "Fuel/Mileage Expenses",
	"Subsidy Parking Claim (S-PARKING CLAIM)": "Subsidiary Parking",
}


def plan_type_accounts(mapping: dict, companies, account_lookup: dict, existing_rows, groups=None) -> dict:
	"""What to add: {type: [(company, account)]} and what is missing, with a
	reason for each miss. Pure.

	`account_lookup` maps (account_name, company) -> Account name for LEDGER
	accounts, the only kind a claim can post to. `groups` is the same for
	accounts that exist as group headings — the usual reason a type is left
	unconfigured, and something HR can act on only if we name it.
	`existing_rows` is a set of (type, company) already configured.
	"""
	rows, missing = {}, []
	# Case-insensitive: HR's sheet says "Fuel/Mileage expenses", the ERP's chart
	# "Fuel/Mileage Expenses"; a capital must not leave a type without its account.
	folded = {(name.casefold(), company): account for (name, company), account in account_lookup.items()}
	folded_groups = {
		(name.casefold(), company): account for (name, company), account in (groups or {}).items()
	}
	for claim_type, gl_name in mapping.items():
		for company in companies:
			if (claim_type, company) in existing_rows:
				continue
			account = folded.get((gl_name.casefold(), company))
			if account:
				rows.setdefault(claim_type, []).append((company, account))
				continue
			group = folded_groups.get((gl_name.casefold(), company))
			reason = (
				f"{group} is a group, not a ledger — pick a ledger under it"
				if group
				else f"no account named {gl_name} in this company"
			)
			missing.append((claim_type, company, gl_name, reason))
	logger.info(
		"[expense_claim_type_mapping] plan: %d row(s) to add, %d (type, company) without the GL account yet",
		sum(len(v) for v in rows.values()),
		len(missing),
	)
	return {"rows": rows, "missing": missing}


def _spellings(mapping: dict) -> list:
	"""Every capitalisation the chart might use for the mapped names."""
	names = set()
	for gl_name in mapping.values():
		names.update({gl_name, gl_name.lower(), gl_name.upper(), gl_name.title()})
	return sorted(names)


def _served_companies() -> list:
	served = frappe.get_all("HRMS ERP Instance Company", pluck="company", distinct=True)
	return served or frappe.get_all("Company", pluck="name")


def preview_expense_claim_type_mapping(mapping: dict | None = None) -> dict:
	"""What the mapping WOULD wire, and why the rest is still unwired. Reads only.

	Split out of `apply_expense_claim_type_mapping` on 11 Sep 2026, after a third
	attempt at "Pull -> GL Accounts" left Subsidy Parking Claim and General &
	Administrative with an empty Accounts table and the dialog saying only
	"Nothing to create. Already here: 49."

	The reason was computed on every run and then thrown away: the pull PREVIEW
	never looked at claim types at all, and the create path put its answer in
	`result["claim_types"]`, which the dialog does not render. So the one thing
	that says WHY a type has no account — "no account named X in this company",
	or "X is a group, not a ledger" — has never once reached the person pressing
	the button.
	"""
	mapping = mapping or MAPPING
	companies = _served_companies()
	found = frappe.get_all(
		"Account",
		filters={"account_name": ("in", _spellings(mapping)), "company": ("in", companies)},
		fields=["name", "account_name", "company", "is_group", "disabled"],
	)
	# Only a ledger can be a claim type's default account; a group heading is
	# reported as one so HR knows what to do about it.
	account_lookup = {(a.account_name, a.company): a.name for a in found if not a.is_group and not a.disabled}
	groups = {(a.account_name, a.company): a.name for a in found if a.is_group}
	existing_rows = {
		(r.parent, r.company)
		for r in frappe.get_all(
			"Expense Claim Account", filters={"parent": ("in", list(mapping))}, fields=["parent", "company"]
		)
	}
	plan = plan_type_accounts(mapping, companies, account_lookup, existing_rows, groups)
	plan["companies"] = len(companies)
	return plan


def apply_expense_claim_type_mapping(mapping: dict | None = None) -> dict:
	"""Create the types that are missing and add the account rows that can be
	added now. Never edits an existing row. Safe to run any number of times."""
	mapping = mapping or MAPPING
	plan = preview_expense_claim_type_mapping(mapping)

	created_types = []
	for claim_type, gl_name in mapping.items():
		if frappe.db.exists("Expense Claim Type", claim_type):
			continue
		frappe.get_doc(
			{"doctype": "Expense Claim Type", "expense_type": claim_type, "description": f"GL: {gl_name}"}
		).insert(ignore_permissions=True)
		created_types.append(claim_type)

	added = 0
	for claim_type, pairs in plan["rows"].items():
		doc = frappe.get_doc("Expense Claim Type", claim_type)
		for company, account in pairs:
			doc.append("accounts", {"company": company, "default_account": account})
			added += 1
		doc.flags.ignore_permissions = True
		doc.save()
	logger.info(
		"[expense_claim_type_mapping] applied: %d type(s) created, %d account row(s) added, %d still without a GL account",
		len(created_types),
		added,
		len(plan["missing"]),
	)
	return {"created_types": created_types, "rows_added": added, "missing": plan["missing"]}
