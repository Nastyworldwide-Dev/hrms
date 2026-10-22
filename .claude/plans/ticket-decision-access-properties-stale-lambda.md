Filed 22 Oct 2026 while landing Manpower Request S2. NOT caused by it.

hrms/api/test_decision_access_properties.py::test_capability_is_exactly_the_shared_decision_access fails:
TypeError: <lambda>() got an unexpected keyword argument 'system_manager_counts' (first case: Leave Application).
The test (last touched b98d3cdff, 29 Sep) patches _is_routed_approver with a lambda; 40d3760a3 (7 Oct) added the
keyword-only `system_manager_counts` argument and the lambda was never updated. Pre-existing on HEAD before S2.
Fix: give the lambda **kwargs (or the real signature) and re-run; the property itself is still wanted.
