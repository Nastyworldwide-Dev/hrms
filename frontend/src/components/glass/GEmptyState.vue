<!--
  GEmptyState — empty state (spec §10.1 #11, copy rules §11.1: always say what
  to do, never "no records found"). Dashed --glass-rim, NOT a glass surface —
  it does not count against §15. Identical at both breakpoints (§20.7).
  Props:
    title  string, required — e.g. "No leave taken this year"
    body   string, required — e.g. "Your applications will appear here once submitted"
-->
<template>
	<div class="g-empty" role="status">
		<p class="g-empty__title">{{ title }}</p>
		<p class="g-empty__body">{{ body }}</p>
	</div>
</template>

<script setup>
defineProps({
	title: { type: String, required: true },
	body: { type: String, required: true },
})
</script>
