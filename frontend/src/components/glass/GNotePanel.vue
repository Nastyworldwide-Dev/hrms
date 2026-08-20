<!--
  GNotePanel — eligibility hint (spec §10.2 #22): glass surface, radius-input,
  mono 10px --accent-ink. Identical at both breakpoints (§20.7).
  Slot: default — the note text (e.g. an overtime eligibility hint).
-->
<template>
	<div class="g-glass g-note" role="note">
		<slot />
	</div>
</template>
