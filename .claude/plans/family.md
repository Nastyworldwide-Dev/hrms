CLASS: a rule that acts on "what changed" when "what it was before" cannot be read. get_doc_before_save() is None outside a normal save, so a non-new claim could not be told from an edit and a legacy figure an approver already read would be cut under them. Unknown history must mean "leave it", never "act".
hrms/hr/doctype/ot_request/ot_request.py:band_typed_claim same-root (fixed here: a saved claim with no earlier version is left as it is)
hrms/hr/doctype/ot_request/ot_request.py:set_day_type_and_rate not-affected — reads the claim, never rewrites it
hrms/sync/runner.py:doc.flags.ignore_validate not-affected — OT Request is not a mirrored transaction (write_block.py), so no unbanded claim arrives that way
hrms/utils/ot_precision.py:half_hour_claim not-affected — pure function, no history involved
