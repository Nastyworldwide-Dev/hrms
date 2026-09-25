GOAL: one radius per screen, type on the iOS ramp (alpha.9 D15-D18)
DONE WHEN: ios-consistency-audit 0 issues on 36 screens; scale gate OK
CHECK: cd frontend && node e2e/ios-consistency-audit.mjs; node design/gates/scale.mjs
