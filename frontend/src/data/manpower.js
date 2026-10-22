import { personalCacheKey } from "@/utils/personalCache"
import { createResource } from "frappe-ui"
import { employeeResource } from "./employee"

// May the signed-in person send a manpower request? HR, or someone with an Active direct report
// (the server decides: hrms.api.manpower.can_request). Requests offers "Request staff" only on a
// plain `true`: while it loads, and when it fails, the entry stays hidden (fail closed).
export const canRequestManpower = createResource({
	url: "hrms.api.manpower.can_request",
	auto: true,
	cache: personalCacheKey("hrms:can_request_manpower"),
})

export const MANPOWER_LIST_FIELDS = [
	"name",
	"employee",
	"employee_name",
	"position_title",
	"headcount",
	"department",
	"urgency",
	"status",
	"hiring_status",
	"docstatus",
	"creation",
]

// Your own requests for the Requests panel. Frappe's permission query already limits the rows to the
// sender, the approver it was shared with and HR; the employee filter keeps THIS list to yours.
// Read per request: until the employee has resolved the filter is "" and matches nothing, never
// "every request I can see" (an approver would see the people they decide for as their own).
export const myManpowerRequests = createResource({
	url: "frappe.client.get_list",
	makeParams() {
		return {
			doctype: "Manpower Request",
			fields: MANPOWER_LIST_FIELDS,
			filters: {
				employee: employeeResource.data?.name || "",
				docstatus: ["!=", 2],
				// a withdrawn one leaves the panel, as a withdrawn leave does; the chips do not count it either
				status: ["!=", "Withdrawn"],
			},
			order_by: "creation desc",
			limit_page_length: 10,
		}
	},
	auto: true,
	cache: personalCacheKey("hrms:my_manpower_requests"),
	transform(data) {
		return data.map((request) => ({ ...request, doctype: "Manpower Request" }))
	},
})

// The number on More's "Staff requests" row: how many approved requests are waiting on HR. Asked only
// when the person is HR (More decides; the server refuses anyone else), so it never runs for staff.
export const manpowerBoardCount = createResource({
	url: "hrms.api.manpower.hr_board",
	cache: personalCacheKey("hrms:manpower_board_count"),
})
