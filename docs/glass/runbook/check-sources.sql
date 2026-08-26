-- Which source does every mirrored row actually claim to come from?
--
-- HOW TO RUN IT, with no terminal and no deploy:
--   1. open  /app/system-console  on the live site (System Manager only)
--   2. set  Type = SQL
--   3. paste this whole file into the Console box
--   4. press Execute
--
-- System Console's SQL mode opens a READ-ONLY transaction
-- (`frappe.db.begin(read_only=True)`), so this cannot write even by accident.
-- Nothing below is anything but SELECT.
--
-- READING THE RESULT
--   source = '(written here)'   the row was created on this hub. Normal for
--                               Leave Application; suspicious for Employee.
--   source = 'Nasty-Live'       mirrored from live.
--   source = 'Nasty-Dev'        the row was last touched by the DEV pull. On a
--                               hub that ran both, this does NOT mean it came
--                               from dev — it means dev synced it last. Some of
--                               these are live employees.
--
-- If a second source appears next to Nasty-Live, do NOT press Purge: it deletes
-- by this column, and this column is the thing that is wrong.
--
-- If a doctype below does not exist on the site, MariaDB errors on that line —
-- delete that one SELECT and its UNION ALL and run the rest.

SELECT 'Employee' AS doctype, COALESCE(synced_from_instance, '(written here)') AS source, COUNT(*) AS rows_held
FROM `tabEmployee` GROUP BY synced_from_instance
UNION ALL
SELECT 'Attendance', COALESCE(synced_from_instance, '(written here)'), COUNT(*)
FROM `tabAttendance` GROUP BY synced_from_instance
UNION ALL
SELECT 'Employee Checkin', COALESCE(synced_from_instance, '(written here)'), COUNT(*)
FROM `tabEmployee Checkin` GROUP BY synced_from_instance
UNION ALL
SELECT 'Leave Ledger Entry', COALESCE(synced_from_instance, '(written here)'), COUNT(*)
FROM `tabLeave Ledger Entry` GROUP BY synced_from_instance
UNION ALL
SELECT 'Leave Allocation', COALESCE(synced_from_instance, '(written here)'), COUNT(*)
FROM `tabLeave Allocation` GROUP BY synced_from_instance
UNION ALL
SELECT 'Leave Application', COALESCE(synced_from_instance, '(written here)'), COUNT(*)
FROM `tabLeave Application` GROUP BY synced_from_instance
UNION ALL
SELECT 'Leave Policy Assignment', COALESCE(synced_from_instance, '(written here)'), COUNT(*)
FROM `tabLeave Policy Assignment` GROUP BY synced_from_instance
UNION ALL
SELECT 'Shift Assignment', COALESCE(synced_from_instance, '(written here)'), COUNT(*)
FROM `tabShift Assignment` GROUP BY synced_from_instance
UNION ALL
SELECT 'Attendance Request', COALESCE(synced_from_instance, '(written here)'), COUNT(*)
FROM `tabAttendance Request` GROUP BY synced_from_instance
UNION ALL
SELECT 'Shift Request', COALESCE(synced_from_instance, '(written here)'), COUNT(*)
FROM `tabShift Request` GROUP BY synced_from_instance
ORDER BY doctype, source;
