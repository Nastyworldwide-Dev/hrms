import test from "node:test"
import assert from "node:assert/strict"

import { notificationRoute } from "../src/utils/notifications.js"

const remote = (name = "RCR-0001") => ({
	reference_document_type: "Remote Checkin Request",
	reference_document_name: name,
})

test("a remote check-in, pending or decided, lands on Approvals", () => {
	// The check-in queue folded into Approvals (AUDIT-PLAN, Approvals row);
	// decided ones are behind its "Check-ins you've already answered" link.
	for (const status of ["Pending", "Approved", "Rejected", undefined]) {
		assert.deepEqual(
			notificationRoute(remote(), status, () => false),
			{ name: "Approvals" }
		)
	}
})

test("time off in lieu and replacement leave land on Approvals — they have no detail page", () => {
	// The derived CompensatoryLeaveRequestDetailView does not exist, so the
	// row rendered as a dead card and the approver could not reach the request
	// the notification was about (alpha.5 review, 23 Sep 2026).
	for (const doctype of ["Compensatory Leave Request", "Replacement Leave Claim"]) {
		assert.deepEqual(
			notificationRoute(
				{ reference_document_type: doctype, reference_document_name: "X-1" },
				undefined,
				() => false
			),
			{ name: "Approvals" },
			doctype
		)
	}
})

test("remote check-ins never derive a DetailView, even if one were registered", () => {
	const route = notificationRoute(remote(), "Approved", () => true)
	assert.equal(route.name, "Approvals")
})

test("other doctypes derive <Doctype>DetailView when the route exists", () => {
	const item = {
		reference_document_type: "Leave Application",
		reference_document_name: "HR-LAP-0001",
	}
	const route = notificationRoute(
		item,
		undefined,
		(n) => n === "LeaveApplicationDetailView"
	)
	assert.deepEqual(route, {
		name: "LeaveApplicationDetailView",
		params: { id: "HR-LAP-0001" },
	})
})

test("an unregistered derived route resolves to null — no dead taps", () => {
	const item = {
		reference_document_type: "Employee Grievance",
		reference_document_name: "GRV-0001",
	}
	assert.equal(
		notificationRoute(item, undefined, () => false),
		null
	)
})

test("a notification with no reference doctype resolves to null", () => {
	assert.equal(
		notificationRoute({ reference_document_name: "X" }, undefined, () => true),
		null
	)
	assert.equal(
		notificationRoute(null, undefined, () => true),
		null
	)
})
