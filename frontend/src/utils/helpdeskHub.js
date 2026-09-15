// The merged Helpdesk page (15 Sep 2026): ONE tab-shell route with a two-pill
// segment — "HR Issues" (Employee Issue, everyone) and "IT Helpdesk" (native
// Helpdesk tickets). Kept free of Vue imports so the route table and the
// pill rules are testable under node:test, the way appLinks.js is.

// Old /issues and /helpdesk both redirect here; the path is NEW so a stale
// bookmark of either still lands on the right pill (see router/helpdeskHub.js).
export const HUB_PATH = "/support"
export const HUB_ROUTE_NAME = "HelpdeskView"

export const HR_TAB = "hr"
export const IT_TAB = "it"
export const HUB_TABS = [HR_TAB, IT_TAB]
export const DEFAULT_TAB = HR_TAB

// per-session memory of the last pill, so a return visit from the sidebar
// reopens where the user left off
export const TAB_STORAGE_KEY = "hrms:helpdesk-tab"

// A query value is untrusted input (typed URL, old notification link):
// anything but a known pill is treated as absent.
export const parseTab = (value) => (HUB_TABS.includes(value) ? value : null)

// query wins, then the remembered pill, then HR Issues — never an unknown
// value, so the segmented control always has a selected option
export const resolveTab = (queryTab, storedTab) =>
	parseTab(queryTab) ?? parseTab(storedTab) ?? DEFAULT_TAB

export const hubLocation = (tab) => ({ path: HUB_PATH, query: { tab } })
