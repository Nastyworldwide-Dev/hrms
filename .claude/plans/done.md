GOAL: VoiceOver hears why Send on Forgot to check out is off (#4855 family)
DONE WHEN: late-checkout-send-says-why describedby test red on HEAD, green now; defaultCheckoutTime invariant holds over a day of check-in times
CHECK: node --test frontend/src/components/__tests__/late-checkout-send-says-why.test.js frontend/src/utils/__tests__/late-checkout-default.test.js
