<!--
  GEmptyState — empty state (spec §10.1 #11, copy rules §11.1: always say what
  to do, never "no records found"). Dashed --glass-rim, NOT a glass surface —
  it does not count against §15. Identical at both breakpoints (§20.7).
  Props:
    title  string, required — e.g. "No leave taken this year"
    body   string, required — e.g. "Your applications will appear here once submitted"
  Slot:
    action — optional. §11.1 says always say WHAT TO DO, and three empty states
             shipped copy that pointed at nothing: "Paid for something for work?
             Claim it here", "claim it here", "Claim the time back here" — with
             no button, no link, and no "here" to tap. If the copy names an
             action, put the action in this slot.
-->
<template>
	<div class="g-empty" role="status">
		<p class="g-empty__title">{{ title }}</p>
		<p class="g-empty__body">{{ body }}</p>
		<div v-if="$slots.action" class="g-empty__action"><slot name="action" /></div>
	</div>
</template>

<script setup>
defineProps({
	title: { type: String, required: true },
	body: { type: String, required: true },
})
</script>
