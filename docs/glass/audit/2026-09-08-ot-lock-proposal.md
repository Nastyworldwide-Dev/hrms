# OT approval reservation: proposed transaction change

Status: reviewable proposal, awaiting schema/index approval. No index or migration has been applied. Application source is unchanged by this proposal.

## Evidence

The local verification site's transaction isolation is `REPEATABLE-READ`. `SHOW INDEX FROM tabOT Request` reports only `PRIMARY(name)`, `creation`, and `modified`.

The native two-connection probe in `2026-09-08-ot-concurrency-probe.py` runs the actual `get_ot_claim_capacity` function with fixed punch entitlement and real SQL reservation reads. Each transaction creates its own synthetic draft, independently receives a 3h allowance against the same employee's 4h cap, and changes its own draft to Approved. The invariant fails: `[3.0, 3.0]` totals 6h. Both transactions are always rolled back. No fixtures are committed and no DDL runs. This isolates the capacity reservation race; it does not claim a complete Frappe Document or HTTP lifecycle test.

Command, from `/home/nabil/verify-bench/sites`:

```sh
/home/nabil/verify-bench/env/bin/python /home/nabil/nadi-fix-overtime/docs/glass/audit/2026-09-08-ot-concurrency-probe.py
```

## Exact proposed index

```sql
CREATE INDEX `ot_employee_status_date`
ON `tabOT Request` (`employee`, `docstatus`, `ot_date`);
```

The proposed idempotent migration calls `frappe.db.add_index("OT Request", ["employee", "docstatus", "ot_date"], "ot_employee_status_date")`. It changes no field, data value, rate or entitlement. It adds storage and write maintenance overhead and may require a metadata lock during deployment. A rollback can drop this named index after rolling back the dependent locking implementation; removing it while the implementation remains active would restore broad locking scans. Exact DDL syntax and deployment duration must be verified on the target database version. No live index creation is authorized by this artifact.

Expected indexed reservation read:

```sql
SELECT name, ot_date, claimed_hours
FROM `tabOT Request`
WHERE employee = %(employee)s
  AND docstatus = 1
  AND ot_date BETWEEN %(month_start)s AND %(month_end)s
  AND status != 'Rejected'
  AND compensation = 'Overtime Pay'
  AND name != %(trusted_current_request)s
ORDER BY ot_date, name
FOR UPDATE;
```

All values are bound parameters. The current request exclusion comes from the persisted controller, never a public parameter. For a new insert omit that exclusion. `EXPLAIN` should use the proposed composite index with an employee/status/date range, instead of a table scan. This is expected, not yet measured: creating an index locally also requires the schema approval. If the optimizer does not choose the bounded access path on realistic fixtures, the implementation must not ship until a stable plan is verified.

## Lifecycle and lock order

1. Acquire Employee row locks for the sorted set of persisted and requested employee IDs before acquiring an OT Request lock. Keep locks until the existing Frappe transaction commits or rolls back; never commit inside a helper.
2. Override `OTRequest.check_if_latest` to acquire those locks before `super().check_if_latest()`. Native Frappe insert and save both call this method; native `load_doc_before_save` then locks the request with `for_update=True`.
3. The public `approval.decide` already locks a request before `doc.submit`. Its OT-only path must acquire the same employee lock first. Other doctype behavior stays unchanged. Coordinate separately with the worker editing `_is_routed_approver`.
4. Compare the now-locked saved employee identity with the identity read before obtaining employee locks. If it changed, abort and ask for retry. Do not acquire a newly discovered employee lock while holding a request lock.
5. Only approval reserves financial capacity. Recompute capacity from a current locking read after the employee lock, then perform the ordinary Frappe submit in that transaction. Draft validation may preview capacity but does not reserve it; rejection retains all nonfinancial trust checks and creates no reservation.
6. Existing draft duplicate semantics stay unchanged. Creation and employee/date edits hold the same employee locks and perform a current duplicate read for active requests before insert/update. The employee prefix allows bounded duplicate lookup even though `docstatus < 2` is a range.

## Acceptance still required

Native transaction tests must cover same employee/different work dates, backdated requests, a snapshot established before waiting for the employee lock, rejection, cancel releasing capacity only on commit, same-day concurrent drafts, employee changes, and different employees running independently. The late waiter must see the winner's committed reservation under `REPEATABLE-READ`.

Indexing plus a consistent application lock order does not by itself prove the absence of every InnoDB gap-lock deadlock, especially two employees inserting into an initially empty indexed range. Test that boundary explicitly. Any database deadlock must roll back the losing transition wholly; no catch may continue with a stale or incomplete reservation total. Never use `SKIP LOCKED`, change global/session transaction isolation, or serialize every employee behind one global mutex to make the test pass.

The native current-read/lock test requires reviewed local schema fixtures once index approval is given. The existing red probe remains useful evidence while that approval is pending. Mixed-shift monthly-cap preservation is a separate correction and must be complete before the concurrency acceptance is treated as financial correctness.
