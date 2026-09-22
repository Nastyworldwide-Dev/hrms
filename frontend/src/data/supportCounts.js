import { createListResource } from "frappe-ui"

import { personalCacheKey } from "@/utils/personalCache"
import { myTickets } from "@/data/helpdesk"

// How many things YOU have open on each side of the Helpdesk (revamp §7).
//
// The hub has had two pills since 15 Sep and neither said whether there was
// anything behind it, so an employee with an unanswered HR issue had to open
// the pill to find out — every time.
//
// COUNTED FROM THE SAME ROWS THE LISTS SHOW. An independent count query is a
// second answer that can disagree with the list it labels, and a pill reading
// "2" over a list of three is worse than a pill reading nothing.

//: The one HR statuses that mean "still yours to watch". Closed and Resolved
//: are done; anything else is in flight. Kept as an allow-list rather than a
//: "not closed" test so a new status has to be classified deliberately.
const OPEN_ISSUE_STATUSES = ["Open", "In Progress", "Pending"]

//: HD Ticket's own words for the same idea. `Replied` means the agent has
//: answered and it is waiting on the EMPLOYEE, which is the most important
//: one to surface — it is the state people forget they are holding.
const OPEN_TICKET_STATUSES = ["Open", "Replied", "Paused"]

export const myIssuesForCount = createListResource({
	doctype: "Employee Issue",
	fields: ["name", "status"],
	// No employee filter: the row scope already limits an employee to their
	// own issues, and an explicit filter here would need the employee id at
	// module scope — which is not loaded yet when this file is imported.
	orderBy: "creation desc",
	pageLength: 50,
	auto: false,
	cache: personalCacheKey("hrms:support-issue-count"),
})

function countOpen(rows, statuses) {
	if (!Array.isArray(rows)) return 0
	return rows.filter((row) => statuses.includes(row?.status)).length
}

export function openIssueCount() {
	return countOpen(myIssuesForCount.data, OPEN_ISSUE_STATUSES)
}

export function openTicketCount() {
	// The IT side reuses the ticket list the pill itself renders, so the count
	// and the rows are literally the same array.
	return countOpen(myTickets.data, OPEN_TICKET_STATUSES)
}

export { OPEN_ISSUE_STATUSES, OPEN_TICKET_STATUSES }
