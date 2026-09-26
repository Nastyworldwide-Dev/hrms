GOAL: every screen at phone and desktop passes alignment, type, contrast and states checks, and the gate keeps it that way
DONE WHEN: design/gates/ios.mjs runs 7 audits (adds page-audit 402/1280 and states-audit) and all are 0
CHECK: set -a && . ./.env && set +a && node design/gates/ios.mjs
