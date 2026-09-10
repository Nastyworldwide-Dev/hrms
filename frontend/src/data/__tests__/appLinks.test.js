// Role visibility on the Apps rows (P&C brief, 10 Sep 2026).
//
// Sibling-app targets and open-redirect safety live in app-links.test.js;
// this file owns who is OFFERED each row.
import { test } from "node:test"
import assert from "node:assert/strict"

import { APP_LINKS, visibleAppLinks } from "../appLinks.js"

// Role visibility (P&C brief, 10 Sep 2026). The Apps rows are the only nav
// entries that leave the PWA, and both targets are department tools rather
// than staff tools: Approva is purchasing and finance approvals, Project
// Board is NPD. Everyone saw both rows, so most of the workforce was being
// offered two doors they cannot open.
//
// This gate is presentational — each app enforces its own permissions on the
// far side. What it buys is that a row is not offered to someone it cannot
// serve.
//
// The role STRINGS are the trap this pins. ERPNext's roles are "Projects
// User" / "Projects Manager" (plural); "Project Manager" without the s is a
// Designation on Employee, not a role, so a check written against it matches
// nobody and the row silently disappears for the people it was meant for.

const rolesFor = (...extra) => ["All", "Employee", ...extra]

test("Approva is offered only to the finance and HR operators", () => {
	for (const role of [
		"Accounts Manager",
		"Accounts User",
		"System Manager",
		"HR Manager",
		"HR User",
	]) {
		const keys = visibleAppLinks(rolesFor(role)).map((l) => l.key)
		assert.ok(keys.includes("approva"), `${role} should see Approva`)
	}
})

test("an ordinary employee is offered neither app", () => {
	assert.deepEqual(
		visibleAppLinks(rolesFor()).map((l) => l.key),
		[]
	)
})

test("Project Board is offered to the projects roles, not to finance-only users", () => {
	for (const role of ["Projects User", "Projects Manager", "HR Manager", "System Manager"]) {
		const keys = visibleAppLinks(rolesFor(role)).map((l) => l.key)
		assert.ok(keys.includes("board"), `${role} should see Project Board`)
	}
	// Accounts User is Approva-only: it is not a projects role.
	const accounts = visibleAppLinks(rolesFor("Accounts User")).map((l) => l.key)
	assert.deepEqual(accounts, ["approva"])
})

test("the singular 'Project Manager' designation grants nothing", () => {
	// If someone rewrites the allowlist against the designation string, this
	// is the test that catches it rather than a user reporting a missing row.
	assert.deepEqual(
		visibleAppLinks(rolesFor("Project Manager")).map((l) => l.key),
		[]
	)
})

test("every app link declares a non-empty allowlist", () => {
	for (const link of APP_LINKS) {
		assert.ok(Array.isArray(link.roles) && link.roles.length, `${link.key} needs roles`)
	}
})

test("visibleAppLinks survives a missing or malformed roles payload", () => {
	// userResource.data is undefined on first paint; the nav must render, not throw.
	for (const bad of [undefined, null, "HR Manager", {}, 0]) {
		assert.deepEqual(visibleAppLinks(bad), [])
	}
})
