GOAL: one visual system: Apple's type pairs and weights, readable contrast, and one aligned column on desktop
DONE WHEN: page-audit phone 20 -> 6 screens, desktop 23 -> 6 (only small type details left); every design gate green; tests green
CHECK: cd frontend && yarn test && W=1280 H=800 node e2e/page-audit.mjs && node ../design/gates/ios.mjs
