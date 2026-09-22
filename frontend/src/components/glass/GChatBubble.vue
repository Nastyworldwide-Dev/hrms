<!--
  GChatBubble — one message in a conversation (helpdesk threads).

  Two sides, one component. The employee's own replies are an accent-tinted
  solid; everyone else's are glass. That asymmetry is the whole point: a
  thread where both sides look alike makes the reader parse names to know who
  said what, and a helpdesk thread is read in a hurry.

  THE SURFACE RULE: NEITHER side is glass. The inline version this replaces put
  .g-glass on the "them" bubble under a v-for, so a twenty-message thread was
  twenty blurred surfaces against the §15 budget of SIX — and blur is the
  expensive thing on a mid-range Android (§15). It went unnoticed because it
  lived in a view, where the surfaces gate counts markup rather than resolving
  a component; moving it into a primitive is what made the gate able to see it.

  §15.2's answer to a repeated surface is to FLATTEN, which is what the balance
  grid, the stat row and the issue list all do. So both sides are solid fills
  over the page background: the reader's own tinted with accent, everyone
  else's with the panel fill. They read as bubbles and cost the screen nothing.

  The tail corner (rounded-br-md / rounded-bl-md) is what makes the bubble
  point at its author. It is part of the shape, not decoration.

  Props:
    mine  boolean — true for the reader's own message
    who   string, required — the author's display name
    when  string — already formatted; the component does no date work
  Slots:
    default — the message body (callers sanitise their own HTML)
-->
<template>
	<div class="g-bubble" :class="mine ? 'g-bubble--mine' : 'g-bubble--theirs'">
		<div class="g-bubble__who">
			{{ who }}<template v-if="when"> · {{ when }}</template>
		</div>
		<div class="g-bubble__body">
			<slot />
		</div>
	</div>
</template>

<script setup>
defineProps({
	mine: { type: Boolean, default: false },
	who: { type: String, required: true },
	when: { type: String, default: "" },
})
</script>
