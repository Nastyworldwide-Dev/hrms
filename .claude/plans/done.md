GOAL: Send on Forgot to check out is never greyed out without a reason on screen (#4855 family)
DONE WHEN: late-checkout-send-says-why + late-checkout-default tests red on HEAD, green now
CHECK: node --test frontend/src/components/__tests__/late-checkout-send-says-why.test.js frontend/src/utils/__tests__/late-checkout-default.test.js
