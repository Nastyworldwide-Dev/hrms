CLASS: an OT Request fact HR needs in the Desk report that the doctype never stored (approval time; paid state) — follow-up to 38f6087ba's review
hrms/hr/doctype/ot_request/ot_request.py:stamp_approved_on same-root — approval time always the submit's own moment; a planted draft value is replaced, a rejection carries none
hrms/patches/v16_0/ot_request_approved_on_and_payment.py:mirror_level_one_permissions same-root — sites with Custom DocPerm rows get the level-1 rows (else Frappe ignores the JSON and HR cannot set Payment)
hrms/api/approval.py:decide not-affected — reaches doc.submit(), so on_submit stamps as before
