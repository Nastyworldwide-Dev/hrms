-- Is one person in this hub twice, under two different employee IDs?
--
-- HOW TO RUN IT, no terminal, no deploy:
--   1. open  /app/system-console  on the live site (System Manager only)
--   2. set  Type = SQL
--   3. paste ONE block below at a time
--   4. press Execute
--
-- System Console's SQL mode opens a READ-ONLY transaction, so this cannot write.
--
-- WHY IT MATTERS — this is the leading hypothesis for the leave duplicate
-- ("the first request was approved and a second one went through anyway").
--
-- LeaveApplication.validate_leave_overlap is correct and does run on validate.
-- It refuses a second application when one already exists for the SAME employee
-- with docstatus < 2 and status Open or Approved. It has one blind spot, and it
-- is not in the code: the filter is `employee == self.employee`, an employee ID.
--
-- The hub keys mirrored rows on the SOURCE's document name, and Employee uses a
-- naming series. So if the dev ERP calls someone HR-EMP-00042 and the live ERP
-- calls the same human HR-EMP-00113, this hub holds BOTH as separate employees.
-- Leave booked against one is invisible to a check on the other, and the guard
-- lets the second one straight through — while looking, in the code, exactly
-- like it is working.
--
-- READING THE RESULT
--   0 rows everywhere ....... this hypothesis is wrong; look elsewhere (below)
--   any row with two sources  one human, two records, from two instances
--   any row, one source ..... a genuine duplicate on that source; still splits
--                             the leave history and still defeats the guard
--
-- DO NOT delete either record. Merging employees moves attendance, leave
-- ledger entries and salary history; deleting one silently destroys whichever
-- half hangs off it. Decide which ID is authoritative first.

-- 1. Same login. The strongest signal — a User can only belong to one person.
SELECT user_id AS identity, COUNT(*) AS records,
       GROUP_CONCAT(name ORDER BY name SEPARATOR ' + ') AS employee_ids,
       GROUP_CONCAT(DISTINCT COALESCE(synced_from_instance, '(local)')) AS sources
FROM `tabEmployee`
WHERE user_id IS NOT NULL AND user_id != '' AND status != 'Left'
GROUP BY user_id HAVING COUNT(*) > 1;

-- 2. Same personal email.
SELECT personal_email AS identity, COUNT(*) AS records,
       GROUP_CONCAT(name ORDER BY name SEPARATOR ' + ') AS employee_ids,
       GROUP_CONCAT(DISTINCT COALESCE(synced_from_instance, '(local)')) AS sources
FROM `tabEmployee`
WHERE personal_email IS NOT NULL AND personal_email != '' AND status != 'Left'
GROUP BY personal_email HAVING COUNT(*) > 1;

-- 3. Same company email.
SELECT company_email AS identity, COUNT(*) AS records,
       GROUP_CONCAT(name ORDER BY name SEPARATOR ' + ') AS employee_ids,
       GROUP_CONCAT(DISTINCT COALESCE(synced_from_instance, '(local)')) AS sources
FROM `tabEmployee`
WHERE company_email IS NOT NULL AND company_email != '' AND status != 'Left'
GROUP BY company_email HAVING COUNT(*) > 1;

-- 4. Same name. Weakest — real people share names — so treat as a prompt to
--    look, not a finding. Two records with the same name AND the same date of
--    birth is not a coincidence.
SELECT employee_name AS identity, COUNT(*) AS records,
       GROUP_CONCAT(name ORDER BY name SEPARATOR ' + ') AS employee_ids,
       GROUP_CONCAT(DISTINCT COALESCE(date_of_birth, '?')) AS dobs,
       GROUP_CONCAT(DISTINCT COALESCE(synced_from_instance, '(local)')) AS sources
FROM `tabEmployee`
WHERE employee_name IS NOT NULL AND status != 'Left'
GROUP BY employee_name HAVING COUNT(*) > 1;


-- IF ALL FOUR RETURN NOTHING, the duplicate-employee theory is wrong. Run this
-- instead: it lists leave that actually overlaps for a SINGLE employee, which
-- is the thing the guard is supposed to make impossible. Any row here is a real
-- escape and narrows the cause to one of:
--   * the first application's status was not Open/Approved when the second was
--     submitted (the guard only looks at those two);
--   * the second row was written by the SYNC, which inserts with validation
--     off by design — detected daily now by hrms.sync.health.colliding_leave;
--   * both are half-days on the same date, which is legitimately allowed.
SELECT a.employee, a.employee_name,
       a.name AS first_request,  a.status AS first_status,
       b.name AS second_request, b.status AS second_status,
       a.from_date, a.to_date, b.from_date AS b_from, b.to_date AS b_to,
       COALESCE(a.synced_from_instance, '(local)') AS first_source,
       COALESCE(b.synced_from_instance, '(local)') AS second_source,
       a.half_day AS a_half, b.half_day AS b_half
FROM `tabLeave Application` a
JOIN `tabLeave Application` b
  ON a.employee = b.employee
 AND a.name < b.name
 AND a.to_date >= b.from_date
 AND a.from_date <= b.to_date
WHERE a.docstatus < 2 AND b.docstatus < 2
  AND a.status IN ('Open', 'Approved')
  AND b.status IN ('Open', 'Approved')
ORDER BY a.employee, a.from_date;
