<!--
  GClock — check-in clock (spec §10.2 #21): display 36/800/−0.02em, seconds
  15px/600 at opacity .55. Not a surface; it sits on one.
  Identical at both breakpoints (§20.7).

  SECONDS ARE DECORATIVE (§10.2 #21 states this outright), so they are
  aria-hidden and the accessible name carries the time without them.

  On §2.5 — the reading holds, and narrowly. §2.5's letter forbids opacity on
  --ink2 / --ink3 to manufacture a lighter TEXT colour; the seconds apply .55
  to --ink, and are not information. Measured over glass the result is 4.26
  light / 6.03 dark: below the 4.5 §14.1 requires of body text, and at 15px/600
  they are not "large text" either. That is consistent only while they stay
  decorative — the moment anything depends on reading the seconds, this fails
  §14.1 and the opacity has to go, exactly as §14.4 exception 1 removed the
  eyebrow's .6.

  Props:
    time     string, required — e.g. "6:17"
    seconds  string — e.g. "42"; omitted renders no seconds
    suffix   string — e.g. "pm", announced as part of the time
-->
<template>
	<div class="g-clock">
		<span class="g-sr">{{ time }}{{ suffix ? ` ${suffix}` : "" }}</span>
		<span class="g-clock__time" aria-hidden="true">{{ time }}</span>
		<span v-if="seconds" class="g-clock__seconds" aria-hidden="true">{{ seconds }}</span>
		<span v-if="suffix" class="g-clock__seconds" aria-hidden="true">{{ suffix }}</span>
	</div>
</template>

<script setup>
defineProps({
	time: { type: String, required: true },
	seconds: { type: String, default: "" },
	suffix: { type: String, default: "" },
})
</script>
