CLASS: an OT Request fact HR needs in the Desk report that the doctype never stored (approval time; paid state)
hrms/hr/doctype/ot_request/ot_request.py:on_submit same-root — stamps approved_on when an approving submit runs (Desk Submit and api.approval.decide both reach doc.submit())
hrms/api/approval.py:decide not-affected — calls doc.submit(), so the stamp happens in on_submit, not here
frontend/src/views/ot/OTRequestForm.vue same-root — new claim form hides both decision-time fields
