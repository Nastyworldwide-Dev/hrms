<!--
  The Undo bar (owner, 29 Sep 2026, alpha.21): "Withdrawn · Undo", above the
  tab bar for a few seconds. Replaces an "Are you sure? This cannot be undone"
  dialog: doing it, with a way back, is faster and forgives a slip (Apple:
  prefer undo to confirmation). Announced, and Undo is a real button.
-->
<template>
	<Transition name="g-undo">
		<div v-if="undoBar.open" class="g-undo" role="status">
			<span class="g-undo__text">{{ undoBar.message }}</span>
			<button type="button" class="g-undo__action g-focusable" @click="undo">{{ __("Undo") }}</button>
		</div>
	</Transition>
</template>

<script setup>
import { inject } from "vue"

import { closeUndo, undoBar } from "@/data/undoBar"

const __ = inject("$translate")

function undo() {
	console.info("[UndoBar] undo pressed")
	undoBar.pending?.undo()
	undoBar.onUndo?.()
	closeUndo()
}

// Leaving or reloading the page must not lose the action waiting on the bar.
if (typeof window !== "undefined") {
	window.addEventListener("pagehide", () => undoBar.pending?.flush())
}
</script>
