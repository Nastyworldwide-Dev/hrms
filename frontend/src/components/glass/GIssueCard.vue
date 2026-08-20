<!--
  GIssueCard — issue card (spec §10.2 #14). A glass surface in its own right:
  §15.2 counts the Issues screen's two issue cards as two surfaces. Never place
  one inside GListPanel or GBalanceGrid — that nests glass (§15).
  radius-banner 16px, pad 13px, mono ID row + badge, title 12.5/600,
  meta 10px --ink2. Identical at both breakpoints (§20.7).

  Props:
    issueId   string, required — e.g. "HR-2026-0043", rendered mono + tabular
    title     string, required
    meta      string — e.g. "Reported 2 days ago"
    tappable  boolean, default true — renders <button>, two-tone focus ring
  Slots:
    badge     — GBadge (open/resolved) or GStatusChip; the status word is the
                signal, never colour alone (§14.1)
  Emits: click (tappable only)
-->
<template>
	<component
		:is="tappable ? 'button' : 'div'"
		:type="tappable ? 'button' : undefined"
		class="g-glass g-issue"
		:class="{ 'g-focusable': tappable }"
		@click="tappable && $emit('click', $event)"
	>
		<span class="g-issue__top">
			<span class="g-issue__id">{{ issueId }}</span>
			<slot name="badge" />
		</span>
		<span class="g-issue__title">{{ title }}</span>
		<span v-if="meta" class="g-issue__meta">{{ meta }}</span>
	</component>
</template>

<script setup>
defineProps({
	issueId: { type: String, required: true },
	title: { type: String, required: true },
	meta: { type: String, default: "" },
	tappable: { type: Boolean, default: true },
})
defineEmits(["click"])
</script>

<style scoped>
/* the card stacks; .g-issue owns padding and radius */
.g-issue {
	display: block;
	width: 100%;
	text-align: left;
	cursor: pointer;
}
.g-issue__title,
.g-issue__meta {
	display: block;
}
</style>
