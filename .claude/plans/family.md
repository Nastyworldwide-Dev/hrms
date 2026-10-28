CLASS: photo access — the endpoint lost its whitelist when the rule was inserted above it; System Manager-with-an-Employee skipped the company fence
hrms/api/org_chart.py photo same-root — one pure rule _may_see_photo, table-tested over HR, System Manager, staff, unlinked/Left/ambiguous login; Desk permission never decides
hrms/api/org_chart.py get_node not-affected — require_employee refuses a login with no Employee before any read; staff fenced by _fence
hrms/patches/v16_0/repair_public_selfies.py:50 not-affected — a log line mentioning 'photo'; the patch never calls photo
