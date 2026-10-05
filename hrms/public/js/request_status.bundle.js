// Copyright (c) 2026, Nastyworldwide-Dev and contributors
// License: GNU General Public License v3. See license.txt

// One word for one state, in Desk as in Nadi (owner, 5 Oct 2026: "eliminate confusion for anyone who
// uses Nadi and Desk"). Nadi says Waiting / Approved / Rejected / Cancelled
// (frontend/src/utils/requestStatus.js); Desk said Draft (red), Open or Pending for the same request.
//
// The STORED words are untouched (Open, Draft, Pending stay in the database: filters, reports and
// every existing row use them). Only the label changes. A request is waiting until it is SUBMITTED,
// whatever its status field says: a leave saved in Desk as "Approved" without a submit has moved no
// balance and written no attendance (proven 5 Oct 2026), and it must not read as approved.
//
// This file only DEFINES the function. Each doctype's own *_list.js assigns listview_settings and
// calls it (a boot bundle that assigns listview_settings is discarded: desk-listview-settings-one-owner).
// Tests: request_status.bundle.test.js

frappe.provide("hrms.request_status");

// the settings every submittable request list shares; a list script spreads these in
hrms.request_status.indicator = function (doc) {
	if (doc.docstatus === 0 || doc.docstatus === "0") {
		return [__("Waiting"), "orange", "docstatus,=,0"];
	}
	if (doc.docstatus === 2 || doc.docstatus === "2") {
		return [__("Cancelled"), "red", "docstatus,=,2"];
	}
	if (doc.status === "Rejected") return [__("Rejected"), "red", "status,=,Rejected"];
	// submitted: the decision was carried out. A submitted row still holding the old waiting word
	// (Open / Draft) was approved by submitting, as the app reads it.
	return [__("Approved"), "green", "docstatus,=,1"];
};
