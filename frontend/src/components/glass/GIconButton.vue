<!--
  GIconButton — an icon-only control with a real accessible name.

  THREE DEFECTS THIS COLLAPSES (8.6). Every icon-only button in the app was a
  frappe-ui `<Button variant="ghost">` wrapping a bare FeatherIcon, which meant:

    · NO ACCESSIBLE NAME. axe reported `button-name` on 46 of 76 screen-themes
      — 66 nodes. To a screen reader they were all just "button". It was four
      distinct elements repeated across the app, not 62 separate bugs.
    · UNDER THE TOUCH MINIMUM. Measured 28×28, against §14.1's 44px.
    · TWO BACK AFFORDANCES. chevron-left on lists and forms, arrow-left on the
      settings screens. Standardised on chevron-left: it is what the majority
      of navigation already used, and it is the back convention on iOS, which
      is the Ionic mode this app runs in.

  `label` is REQUIRED and becomes aria-label. That is the whole point of the
  component — an icon-only control with no name is not a control, and making
  the name impossible to forget is the only fix that stays fixed.

  Props:
    label  string, required — the accessible name, e.g. "Back", "Filter list"
    flush  boolean — pull the target out to the screen gutter. A 44px box at
           the edge would otherwise indent the glyph past the content column;
           the target stays 44px, only the optical position moves.
  Emits: click
-->
<template>
	<button
		type="button"
		class="g-iconbtn g-focusable"
		:class="{ 'g-iconbtn--flush': flush }"
		:aria-label="label"
		@click="$emit('click', $event)"
	>
		<slot />
	</button>
</template>

<script setup>
defineProps({
	label: { type: String, required: true },
	flush: { type: Boolean, default: false },
})
defineEmits(["click"])
</script>
