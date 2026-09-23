CLASS: More listing what another page owns (audit-pages §4 "Final More").
Leaves and Expenses are requests (PAGE-4); the More eyebrow repeated the
title (PAGE-10); public holidays had no door but the Leaves dashboard (PAGE-20).

Readers of NAV_ITEMS / MORE_ITEMS:
frontend/src/data/navItems.js TAB_ITEMS — same-root: indexes into NAV_ITEMS shifted with the removals; re-pointed (Requests 2, Score 3), pinned by tab-bar-2.0.test.js.
frontend/src/views/More.vue — same-root: rows follow MORE_ITEMS; Public holidays row + sheet added; eyebrow removed.
frontend/src/components/SideNav.vue — same-root by data: shows NAV_ITEMS, so Leaves/Expenses leave the desktop side nav too (both still reached from Requests' balances).
frontend/src/data/navItems.js More `routes` — not-affected: /dashboard/leaves and /dashboard/expense-claims stay listed so the bar still lights More when standing on them.
frontend/src/views/leave/Dashboard.vue — same-root: its second holiday list removed (one list, the sheet).
