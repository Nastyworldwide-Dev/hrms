import { createResource } from "frappe-ui"
import { employeeResource } from "./employee"

import dayjs from "@/utils/dayjs"

const transformLeaveData = (data) => {
	return data.map((leave) => {
		leave.leave_dates = getLeaveDates(leave)
		leave.doctype = "Leave Application"
		return leave
	})
}

export const getLeaveDates = (leave) => {
	if (leave.from_date == leave.to_date)
		return dayjs(leave.from_date).format("D MMM")
	else
		return `${dayjs(leave.from_date).format("D MMM")} - ${dayjs(
			leave.to_date
		).format("D MMM")}`
}

export const myLeaves = createResource({
	url: "hrms.api.get_leave_applications",
	params: {
		employee: employeeResource.data.name,
		limit: 10,
	},
	auto: true,
	cache: "hrms:my_leaves",
	transform(data) {
		return transformLeaveData(data)
	},
	onSuccess() {
		leaveBalance.reload()
	},
})

export const teamLeaves = createResource({
	url: "hrms.api.get_leave_applications",
	params: {
		employee: employeeResource.data.name,
		approver_id: employeeResource.data.user_id,
		for_approval: 1,
		limit: 10,
	},
	auto: true,
	cache: "hrms:team_leaves",
	transform(data) {
		return transformLeaveData(data)
	},
})

// decided by me — the approval trail Team Requests loses on decision
export const historyLeaves = createResource({
	url: "hrms.api.get_leave_applications",
	params: {
		employee: employeeResource.data.name,
		approver_id: employeeResource.data.user_id,
		history: 1,
		limit: 10,
	},
	auto: true,
	cache: "hrms:history_leaves",
	transform(data) {
		return transformLeaveData(data)
	},
})

export const leaveBalance = createResource({
	url: "hrms.api.get_leave_balance_map",
	auto: true,
	cache: "hrms:leave_balance",
	transform: (data) => {
		// Gauge denominator = annual entitlement; the server falls back to
		// allocated, the || below only covers older cached payloads
		return Object.fromEntries(
			Object.entries(data).map(([leave_type, allocation]) => {
				const entitlement =
					allocation.annual_entitlement || allocation.allocated_leaves
				allocation.annual_entitlement = entitlement
				allocation.balance_percentage = entitlement
					? Math.min((allocation.balance_leaves / entitlement) * 100, 100)
					: 0
				// band between allocated and entitlement = headroom a pro-rated
				// joiner does not get this year
				allocation.prorated = entitlement - allocation.allocated_leaves > 0.01
				allocation.prorated_percentage = allocation.prorated
					? ((entitlement - allocation.allocated_leaves) / entitlement) * 100
					: 0
				allocation.period_year = allocation.from_date
					? dayjs(allocation.from_date).year()
					: dayjs().year()
				return [leave_type, allocation]
			})
		)
	},
})
