GOAL: the two sheets no audit had opened (calendar day, approval) follow the iOS rules; every design gate green
DONE WHEN: sheet-consistency-audit 12/12 ok, ios gate 0, coherence 0, usage 0 new, a11y 0 new; frontend tests 1383 pass
CHECK: cd frontend && set -a && . ../.env && set +a && node e2e/sheet-consistency-audit.mjs && node ../design/gates/ios.mjs
