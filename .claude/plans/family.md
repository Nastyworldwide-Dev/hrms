CLASS: a 404/DoesNotExistError read as "this record was deleted" where the resource is not one record
frontend/src/components/ResourceError.vue same-root — fixed: gone only with the `record` prop
frontend/src/views/{sop/SopDetail,helpdesk/TicketDetail,announcements/Detail,manpower/ManpowerRequestDetail}.vue same-root — marked record
frontend/src/views/helpdesk/HelpdeskList.vue, TicketNew.vue, ListView.vue, KPI/board/list resources not-affected — no record prop, keep Could not load + Try again
hrms/api/helpdesk.py get_ticket ticket .claude/plans/ticket-load-shifts-oct25.md — Helpdesk missing raises DoesNotExistError, a direct ticket link then reads "no longer here"
frontend/src/utils/requestFailure.js noAccessDrawn ticket .claude/plans/ticket-loudrequest-split.md — any visible data-no-access on the page silences another request toast
