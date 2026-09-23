CLASS: a resource whose params are read once from another async resource.
createResource captures params at construction; HolidayList read
$employee.data.name, so opening the sheet before it resolved asked for
nobody's holidays and never retried (review of 40133f8f3).

Call sites of HolidayList:
frontend/src/views/More.vue — same-root, fixed here (mounts only once employee.data is there).

Also: HelpdeskHub.test.js still pinned the "Helpdesk" title the same commit
renamed to "Help"; it follows the rule's new wording.
