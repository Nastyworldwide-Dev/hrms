# Ticket: the approver EMAIL is not routed up the line (5 Oct 2026, flows hunt M2)
leave_application.py notify_leave_approver (~802) emails `self.leave_approver` only. With no approver named it sends
nothing, while the PWA notice now reaches the employee's line (pwa_notifications._get_doc_approver). A staff member who
reads email, not the app, still hears nothing for an unnamed-approver leave. Not changed here: it changes who receives
an email (a rule), and Expense Claim / Shift Request may differ. Owner to say whether the email should follow the line.
