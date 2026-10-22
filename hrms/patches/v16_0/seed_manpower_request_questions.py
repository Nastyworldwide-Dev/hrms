"""Fill Manpower Request Settings with the questions of the MS "Manpower Requisition Form".

The fixed questions (department, position, headcount, location, type, how soon, pay) are fields
the system reads. These seven are the rest: HR edits, adds or hides them in Desk afterwards
(owner, 22 Oct 2026: "make it changeable in desk, for hr, so we dont hardcode it").

Only an EMPTY list is filled, so a second run — or a site where HR already changed the questions —
is left alone.
"""

import logging

import frappe

logger = logging.getLogger(__name__)

STEP_WHY = "3 Why"
STEP_REQUIREMENTS = "5 Requirements"

QUESTIONS = (
	{
		"step": STEP_REQUIREMENTS,
		"question": "Draft job description",
		"answer_type": "Long text",
		"required": 1,
	},
	{"step": STEP_REQUIREMENTS, "question": "KPIs", "answer_type": "Long text"},
	{
		"step": STEP_REQUIREMENTS,
		"question": "Minimum qualification",
		"answer_type": "Choice",
		"choices": "Diploma\nBachelor's Degree\nProfessional Certification\nSPM / O' Level",
	},
	{
		"step": STEP_REQUIREMENTS,
		"question": "Experience",
		"answer_type": "Choice",
		"choices": "Fresh Graduate\n1–3 years\n3–5 years\n5+ years",
	},
	{
		"step": STEP_REQUIREMENTS,
		"question": "Industry experience required",
		"answer_type": "Choice",
		"choices": "Yes\nNo\nOther",
	},
	{"step": STEP_REQUIREMENTS, "question": "If other, which industry", "answer_type": "Short text"},
	{"step": STEP_WHY, "question": "What happens if it is late?", "answer_type": "Long text"},
)


def execute():
	settings = frappe.get_doc("Manpower Request Settings")
	if settings.questions:
		logger.info("[patch] Manpower Request Settings already has questions; left alone")
		return
	for question in QUESTIONS:
		settings.append("questions", {"required": 0, "active": 1, **question})
	settings.save(ignore_permissions=True)
	logger.info("[patch] seeded %d Manpower Request question(s)", len(QUESTIONS))
