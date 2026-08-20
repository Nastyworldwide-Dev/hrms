<!--
  GStatusChip — workflow status (spec §10.3 #28: "currently undefined in
  either document").

  PROPOSAL — the spec defines no mapping; this one reuses badge tokens only,
  every pair computed ≥ 4.5:1 on both themes (composited over glass):
    Draft      ink2 on icon-bg                 5.75 / 5.85
    Submitted  accent-ink on brand-14% tint    7.02 / 10.16
    Approved   success-ink on success-20%      4.60 / 6.88  (= RESOLVED badge)
    Rejected   on-brand on solid danger fill   7.11 / 7.11  (tinted danger
               cannot reach 4.5 on light — 3.98 at 14% — so rejected goes solid)
    Cancelled  ink-muted on plain glass, 1px --hair outline   4.56 / 4.58
  Flagged in the phase-2 HANDOFF; confirm or amend before phase 5 sweeps.

  Props:
    status  "Draft" | "Submitted" | "Approved" | "Rejected" | "Cancelled"
            (case-insensitive). Renders the status word — text is the signal,
            never colour alone (§14.1).
-->
<template>
	<span class="g-badge" :class="`g-chip--${normalized}`">
		{{ status }}
	</span>
</template>

<script setup>
import { computed } from "vue"

const props = defineProps({
	status: {
		type: String,
		required: true,
		validator: (v) =>
			["draft", "submitted", "approved", "rejected", "cancelled"].includes(v.toLowerCase()),
	},
})

const normalized = computed(() => props.status.toLowerCase())
</script>
