// Pure filter/count logic for the HR Issue Board — kept free of Vue/window
// so it stays testable with node --test (frontend/tests/issue-board.test.mjs).

export const ISSUE_STATUSES = ["Open", "In Progress", "Completed"]

// who gets the board instead of the personal list (presentation only —
// server-side row scope is the real protection)
export const HR_BOARD_ROLES = ["HR User", "HR Manager", "System Manager"]
export const hasHRRole = (roles) =>
	(roles || []).some((role) => HR_BOARD_ROLES.includes(role))

export const filterIssues = (issues, { status, issueType, search } = {}) => {
	const query = (search || "").toLowerCase().trim()
	return (issues || []).filter((issue) => {
		if (status && issue.status !== status) return false
		if (issueType && issue.issue_type !== issueType) return false
		if (query) {
			const haystack = [issue.name, issue.employee_name, issue.department, issue.details]
				.filter(Boolean)
				.join(" ")
				.toLowerCase()
			if (!haystack.includes(query)) return false
		}
		return true
	})
}

export const countByStatus = (issues) => {
	const counts = Object.fromEntries(ISSUE_STATUSES.map((status) => [status, 0]))
	let high = 0
	for (const issue of issues || []) {
		if (issue.status in counts) counts[issue.status] += 1
		if (issue.urgency === "High" && issue.status !== "Completed") high += 1
	}
	return { ...counts, high }
}
