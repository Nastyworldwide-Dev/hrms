GOAL: All balances sheet shows a ring per leave type (owner pick B, 19 Oct 2026)
DONE WHEN: ring tests green; build green; bench summary rows carry allocated + taken
CHECK: cd frontend && node --test src/utils/__tests__/ring-arcs.test.js src/components/__tests__/balances-rings.test.js
