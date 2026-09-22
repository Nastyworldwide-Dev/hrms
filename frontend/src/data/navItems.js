import {
	BookOpenText,
	CalendarDays,
	ChartLine,
	CircleCheckBig,
	Ellipsis,
	Headphones,
	House,
	Kanban,
	CircleDollarSign,
	FileText,
} from "lucide-vue-next"
import { markRaw } from "vue"

import { visibleAppLinks } from "@/data/appLinks"
import { HUB_PATH } from "@/utils/helpdeskHub"

// Single source of truth for primary navigation, consumed by both shells
// (BottomTabs on phone, SideNav on lg+). `title` and `shortTitle` are i18n
// source strings — consumers must wrap them with the injected $translate.
// `shortTitle` is the design's compact tab-bar label. The phone bar shows
// TAB_ITEMS (5 primaries + More); SideNav shows the full NAV_ITEMS list.
const NAV_ITEMS = [
	{ icon: markRaw(House), title: "Home", shortTitle: "Home", route: "/home" },
	{
		// "Calendar", not "Attendance" (2.0 slice 0.1, UX_PLAN §3.2: "Calendar
		// (today: Attendance)"). The same screen — it already is a month grid.
		// "Attendance" is what HR calls the record; "Calendar" is what an
		// employee calls the thing they open to see their month.
		icon: markRaw(CalendarDays),
		title: "Calendar",
		shortTitle: "Calendar",
		route: "/dashboard/attendance",
	},
	{
		icon: markRaw(CalendarDays),
		title: "Leaves",
		shortTitle: "Leaves",
		route: "/dashboard/leaves",
	},
	{
		// The one genuinely new destination (UX_PLAN §3.3). What it is for was
		// spread across three places — starting a request in Home's quick
		// links, watching one in Home's request panel, the per-type lists on
		// two dashboards — so "where is my leave application?" had three
		// plausible answers and no obvious one.
		icon: markRaw(FileText),
		title: "Requests",
		shortTitle: "Requests",
		route: "/requests",
	},
	{
		icon: markRaw(CircleDollarSign),
		title: "Expenses",
		shortTitle: "Expenses",
		route: "/dashboard/expense-claims",
	},
	{
		// "Score", not "KPI" (UX_PLAN §3.6: "Score screen is a reroute"). Same
		// screen, the employee's word for it. Doubt on record in Q1 and worth
		// keeping: a quarterly screen in a daily bar — revisit with four weeks
		// of usage.
		icon: markRaw(ChartLine),
		title: "Score",
		shortTitle: "Score",
		route: "/dashboard/kpi",
	},
	{
		// ONE entry for Issues + Helpdesk (owner, 15 Sep 2026), in the slot
		// Issues held. HR Issues is for everyone, so the entry is never gated;
		// the IT pill inside is what hides on sites without the Helpdesk app.
		icon: markRaw(Headphones),
		title: "Helpdesk",
		shortTitle: "Helpdesk",
		route: HUB_PATH,
	},
	{
		icon: markRaw(BookOpenText),
		title: "SOPs",
		shortTitle: "SOPs",
		route: "/sop",
	},
]

// Phone tab bar — FIVE fixed destinations (spec §13.1, §10.1 #8). A bar whose
// destinations change under the user breaks Ionic's per-tab navigation stacks,
// which is why the count is fixed rather than "whatever fits".
//
// §13.1 recommends HOME · ATTEND · LEAVE · PAY · MORE. There is no Pay screen
// in this app — no salary-slip route exists, and building one is a new feature
// (§1, out of scope) — so Expenses takes the fourth slot. Flagged for P&C:
// DECISION 2 is not signed off, and the PAY substitution is part of what needs
// confirming.
//
// `routes` lists every path a tab claims for its active state.
export const TAB_ITEMS = [
	NAV_ITEMS[0], // Home
	NAV_ITEMS[1], // Calendar — was Attendance
	NAV_ITEMS[3], // Requests
	NAV_ITEMS[5], // Score — was KPI
	{
		// More
		icon: markRaw(Ellipsis),
		title: "More",
		shortTitle: "More",
		route: "/more",
		// Leaves and Expenses LOST THEIR TAB, not their screen: they are one
		// tap further away, under More, and their routes are listed here so
		// the bar lights More up when the employee is on one. A destination
		// that moved without being listed leaves the bar showing nothing
		// selected.
		routes: [
			"/more",
			"/dashboard/leaves",
			"/dashboard/expense-claims",
			HUB_PATH,
			"/sop",
			"/team",
			"/remote-approvals",
		],
	},
]

// Everything not in the tab bar. The 2.0 bar (slice 0.1) took KPI up as Score
// and dropped Leaves and Expenses down here, so the slice index no longer
// describes the split — More is now "every nav item whose route no tab owns",
// computed rather than counted, because a hand-kept index silently rots the
// moment the bar changes again.
const TAB_ROUTES = new Set(TAB_ITEMS.map((item) => item.route))
export const MORE_ITEMS = NAV_ITEMS.filter((item) => !TAB_ROUTES.has(item.route))

// Sibling apps reached by leaving the PWA (see data/appLinks.js). Rendered as
// their own "Apps" group under More and below the SideNav divider; never in the
// phone tab bar, whose five destinations are fixed.
const APP_ICONS = {
	approva: markRaw(CircleCheckBig),
	board: markRaw(Kanban),
}

// The rows this user may be offered, icons attached. Both shells (More on the
// phone, SideNav on lg+) render the same list, so the allowlist is applied
// once here rather than twice in the views — the two cannot drift apart.
// Pass `get_current_user_info().roles`; an absent payload yields [].
export const visibleAppItems = (userRoles) =>
	visibleAppLinks(userRoles).map((link) => ({ ...link, icon: APP_ICONS[link.key] }))
