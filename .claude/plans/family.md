CLASS: waiting on an Ionic event that Ionic 7 never sends (ionRefreshComplete).

Call sites: frontend/src/components/glass/GPullRefresh.vue onRefresh — same-root, fixed (reset on ionStart; 10 s completion cap). grep ionRefreshComplete in src — no other site, not-affected. Callers Home/Requests/Approvals/Announcements/ListView call complete() — not-affected (cap covers a rejected reload).
