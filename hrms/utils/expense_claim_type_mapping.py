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
import re

import frappe

logger = logging.getLogger(__name__)

#: Claim type (exactly as HR wrote it) -> account name in the ERP's chart.
MAPPING = {
	"Car Rental (CAR RENTAL)": "Travel Expenses",
	"Flight / Public Transport (FLIGHT/PT)": "Travel Expenses",
	# HR's sheet spells this "General & Administrartive" and the source chart uses
	# "General And Administrative". Any of them resolves; the first is what the
	# claim type's description shows.
	"General & Administrative (G&A)": ("General & Administrative", "General & Administrartive"),
	"Gym & Wellness Subsidy (GYM&WS)": "Employee Benefits",
	"Lodging / Hotel (LODGING/HOTEL)": "Travel Expenses",
	"Meals & Entertainment (M&E)": "Employee Meals & Entertainment",
	"Mileage (CAR) (MILEAGE CAR)": "Fuel/Mileage Expenses",
	"Mileage (Motorcycle) (MILEAGE MOTORCYCLE)": "Fuel/Mileage Expenses",
	"Parking & Toll (PARKING&TOLL)": "Parking & Toll",
	"Petrol (PETROL)": "Fuel/Mileage Expenses",
	# HR's sheet spells this "Subsidary Parking" — one "i" short. Normalising
	# cannot bridge two different words, and guessing across words is how a claim
	# gets wired to the wrong account, so both spellings are named instead.
	"Subsidy Parking Claim (S-PARKING CLAIM)": ("Subsidiary Parking", "Subsidary Parking"),
}


def gl_names_for(value) -> list:
	"""The GL account names a claim type accepts, canonical first.

	A mapping value is either one name or a tuple of spellings. HR's sheet and
	the ERP's chart disagree on two rows by a single letter, and normalising
	cannot bridge two different words — "subsidary" and "subsidiary" are not the
	same word, and treating them as one is how a claim reaches the wrong GL
	account. Naming both is honest; guessing is not.
	"""
	if isinstance(value, str):
		return [value]
	return list(value)


def normalise_account_name(name: str) -> str:
	"""A GL account name reduced to what actually identifies it.

	Case, "&" against the word "and", punctuation and repeated spaces all vary
	between two charts that mean the same account, and the pull used to require
	an exact hit. One character out and the account was invisible to it.

	Deliberately conservative: it collapses spelling, never meaning. "Subsidy"
	and "Subsidiary" stay different words, because wiring a claim to the wrong
	GL account is worse than leaving it unwired.
	"""
	text = (name or "").casefold().replace("&", " and ")
	text = re.sub(r"[^a-z0-9]+", " ", text)
	return " ".join(text.split())


def match_account_name(wanted: str, candidates: dict):
	"""The candidate account for `wanted`, or None. `candidates` is {name: value}.

	Exact first, then normalised. A normalised key matching MORE than one
	candidate is refused rather than guessed — an ambiguous chart is reported to
	the operator with the candidates named, not resolved by luck.
	"""
	if wanted in candidates:
		return candidates[wanted]
	key = normalise_account_name(wanted)
	hits = [value for name, value in candidates.items() if normalise_account_name(name) == key]
	if len(hits) == 1:
		return hits[0]
	if len(hits) > 1:
		logger.warning(
			"[expense_claim_type_mapping] %r matches %d accounts after normalising — refusing to guess",
			wanted,
			len(hits),
		)
	return None


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
	# Matching is normalised, not merely case-folded: HR's sheet and the ERP's
	# chart differ by capitals, by "&" against "and", by punctuation and by
	# spacing, and an exact comparison here left a type without its account.
	for claim_type, value in mapping.items():
		names = gl_names_for(value)
		for company in companies:
			if (claim_type, company) in existing_rows:
				continue
			ledgers = {name: acct for (name, comp), acct in account_lookup.items() if comp == company}
			headings = {name: acct for (name, comp), acct in (groups or {}).items() if comp == company}
			# Any spelling the claim type names may resolve it — HR's sheet and the
			# ERP's chart differ by a letter on two rows.
			account = next((hit for n in names if (hit := match_account_name(n, ledgers))), None)
			if account:
				rows.setdefault(claim_type, []).append((company, account))
				continue
			group = next((hit for n in names if (hit := match_account_name(n, headings))), None)
			shown = " / ".join(names)
			reason = (
				f"{group} is a group, not a ledger — pick a ledger under it"
				if group
				else f"no account named {shown} in this company"
			)
			missing.append((claim_type, company, shown, reason))
	logger.info(
		"[expense_claim_type_mapping] plan: %d row(s) to add, %d (type, company) without the GL account yet",
		sum(len(v) for v in rows.values()),
		len(missing),
	)
	return {"rows": rows, "missing": missing}


def _spellings(mapping: dict) -> list:
	"""Every capitalisation the chart might use for the mapped names."""
	names = set()
	for value in mapping.values():
		for gl_name in gl_names_for(value):
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
	for claim_type, value in mapping.items():
		gl_name = gl_names_for(value)[0]
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
