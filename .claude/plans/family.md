CLASS: a calendar dated by when a notice is SHOWN, not when the event HAPPENS
hrms/hr/doctype/hr_announcement event_date same-root — new field, required for Event, cleared otherwise
hrms/patches/v16_0/backfill_announcement_event_date same-root — existing Events keep their dot (event_date = publish_from), shadowing Property Setters removed
