GOAL: HR's OT Request report shows Claimed Hours as 1.50, not 1.500000000; storage stays 9 decimals
DONE WHEN: Frappe's real formatter renders 1.50 for the report call; list the same; precision "9" untouched
CHECK: node --test hrms/hr/doctype/ot_request/ot_request_list.test.js
