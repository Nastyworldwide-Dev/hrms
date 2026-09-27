GOAL: Change password says the site's own rule as you type (Frappe test_password_strength); Fix a day says "Also fix rest days and holidays" instead of "Include holidays".
DONE WHEN: hint under the password group from Frappe's answer, none without a policy; plainLabel maps Include Holidays.
CHECK: node --test frontend/src/utils/__tests__/passwordHint.test.js frontend/src/utils/__tests__/plainLabel.test.js; bench with policy on: "password" -> "This is a top-10 common password.", long phrase -> "Strong enough." (policy restored off)
