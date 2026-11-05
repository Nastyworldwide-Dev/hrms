"""Expense claims are approved in two steps: the manager, then HR (owner, 5 Nov 2026).

    Draft          the claim waits for its manager (the reporting manager or the
                   named expense approver: today's approval line, unchanged).
                   Manager approves  -> "Waiting for HR" (nothing posted yet).
                   Manager rejects   -> Rejected, final, as today.
    Waiting for HR the claim waits for HR (HR User / HR Manager, inside their
                   company fence, exactly how HR reaches any request today).
                   HR approves -> Approved, final: submitted and posted, as a
                   manager's approval was before. HR rejects -> Rejected, final.

The owner's words: "hr will work like manager same thing all, just that hr is after
manager". So HR gets no new screens or rules, only a place in the order:

  * HR does not see or act on a claim still waiting for its manager;
  * the manager does not see or act on a claim once it is with HR;
  * an employee with nobody above them goes straight to HR;
  * HR deciding their OWN claim at the HR step is allowed ("any hr including
    themselve"); it is the one place self-approval is permitted.

Pure: no frappe import, so the rule is tested without a bench.
"""

DOCTYPE = "Expense Claim"
MANAGER_STEP = "Draft"
HR_STEP = "Waiting for HR"
PENDING = (MANAGER_STEP, HR_STEP)


def is_pending(status) -> bool:
	"""Still waiting on someone (either step)."""
	return status in PENDING


def step_of(status) -> str | None:
	"""'manager' or 'hr' for a pending claim, else None."""
	if status == MANAGER_STEP:
		return "manager"
	if status == HR_STEP:
		return "hr"
	return None


def may_decide(status, *, on_line: bool, is_hr: bool) -> bool:
	"""May this caller decide the claim at its current step?

	`on_line`: the caller is the claim's manager or named approver (the approval
	line, NOT counting HR). `is_hr`: HR User / HR Manager inside the claim's company
	fence (System Manager alone is not HR here).
	"""
	step = step_of(status)
	if step == "manager":
		return on_line
	if step == "hr":
		return is_hr
	return False


def next_status(status, decision) -> str:
	"""What a decision moves the claim to. Only a manager's approval is not final."""
	if status == MANAGER_STEP and decision == "Approved":
		return HR_STEP
	return decision


def is_final(status, decision) -> bool:
	"""Does this decision submit the claim (and post it, when approved)?"""
	return next_status(status, decision) != HR_STEP


def first_status(has_manager: bool) -> str:
	"""Where a new claim starts: with its manager, or straight with HR if it has none."""
	return MANAGER_STEP if has_manager else HR_STEP
