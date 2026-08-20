<!--
  GStatusChip — workflow status (spec §10.3 #28).

  THE STATE SET IS NOT CLOSED. v1.2 of this component validated against five
  states (Draft/Submitted/Approved/Rejected/Cancelled), which was a guess made
  before the data was read. The app's real workflow states are composite —
  "Approved & Unpaid", "Approved & Submitted", "Approved & Draft" — and Frappe
  workflows are user-configurable, so any closed list is wrong by construction.
  Recorded in spec §10.3 #28.

  So: twelve known states map onto SIX variants, and an unknown state falls back
  to neutral rather than throwing. A chip that refuses to render is worse than
  a chip that renders grey.

  Variants, measured over glass (light / dark):
    neutral    ink2 on icon-bg                       5.75 / 5.85
    progress   accent-ink on brand-14%               7.02 / 10.16
    success    success-ink on success-20%            4.60 / 6.88
    danger     on-brand on SOLID danger              7.11 / 7.11
    muted      ink-muted on glass, hair outline      4.56 / 4.58
    attention  warn-ink on glass, warn outline       4.72 / 8.12

  The status word is always rendered: colour is never the only signal (§14.1).

  Props:
    status  string, required — the raw workflow state, e.g. "Approved & Unpaid".
            Drives the variant; unknown values render neutral.
    label   string — display text. Defaults to `status`; pass the translated
            string where the call site has doctype context, e.g.
            :label="__(status, null, 'Expense Claim')"
-->
<template>
	<span class="g-badge" :class="`g-chip--${variant}`">
		{{ label || status }}
	</span>
</template>

<script setup>
import { computed } from "vue"

// Taken from the chipMaps this component replaces, not invented. Keys are
// compared case-insensitively so "Open" and "open" behave the same.
const STATES = {
	draft: "neutral",
	open: "attention",
	pending: "attention",
	unpaid: "attention",
	submitted: "progress",
	"approved & draft": "progress",
	"approved & unpaid": "progress",
	"approved & submitted": "progress",
	approved: "success",
	paid: "success",
	rejected: "danger",
	cancelled: "muted",
	// attendance states — TeamDashboard mapped these by hand and noted "the DS
	// has no red variant"; it does now, so Absent stops rendering as a brand chip
	present: "success",
	absent: "danger",
	"on leave": "progress",
	"half day": "attention",
}

const props = defineProps({
	status: { type: String, required: true },
	label: { type: String, default: "" },
})

const variant = computed(() => STATES[String(props.status).trim().toLowerCase()] ?? "neutral")
</script>
