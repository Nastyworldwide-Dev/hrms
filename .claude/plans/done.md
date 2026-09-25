GOAL: no page moves while it loads (owner 25 Sep: "jumpy jumpy stuff … every bit measured")
DONE WHEN: scroll-and-shift-audit shows 0 shifts on 36 screens, cold AND warm cache; tests + gates green
CHECK: cd frontend && node e2e/scroll-and-shift-audit.mjs; yarn test; node design/gates/run.mjs
