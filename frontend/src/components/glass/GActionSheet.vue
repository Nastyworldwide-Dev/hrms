<!--
  GActionSheet — action sheet (spec §10.3 #26). Presents through GModal, so it
  inherits the focus-trap workaround (§16.3) rather than re-implementing it.
  Centred dialog at lg: (§20.7 #26) — that comes from GModal.

  SCOPE — this is the sheet CHROME only: surface, title, action rows, dismiss.
  The three existing sheets carry genuinely different business logic and
  incompatible props (RequestActionSheet: fields/modelValue/showOpenForm ·
  WorkflowActionSheet: doc/workflow/view · ListFiltersActionSheet:
  filterConfig/filters + apply/clear/update emits). Collapsing those into one
  component would be a rewrite, not a reskin, and phase 5 only swaps skins.
  So each keeps its logic and renders inside this container via the default
  slot; `actions` covers the simple "list of choices" case they share.

  Not a separate glass surface: GModal owns the surface (§15).

  Props:
    isOpen   boolean — controlled open state
    trigger  string — id of the opening element
    title    string — sheet heading
    actions  array — [{ key, label, destructive, disabled }] for the simple case
  Emits:
    select(key)  — an action row was chosen
    did-dismiss  — passthrough from GModal
  Slot: default — arbitrary sheet content (the three existing sheets go here)
-->
<template>
	<GModal :is-open="isOpen" :trigger="trigger" :title="title" @did-dismiss="$emit('did-dismiss')">
		<slot />

		<button
			v-for="action in actions"
			:key="action.key ?? action.label"
			type="button"
			class="g-sheet__action g-focusable"
			:class="{ 'g-sheet__action--destructive': action.destructive }"
			:aria-disabled="action.disabled || undefined"
			@click="onSelect(action)"
		>
			{{ action.label }}
		</button>
	</GModal>
</template>

<script setup>
import GModal from "./GModal.vue"

defineProps({
	isOpen: { type: Boolean, default: false },
	trigger: { type: String, required: false },
	title: { type: String, default: "" },
	actions: { type: Array, default: () => [] },
})
const emit = defineEmits(["select", "did-dismiss"])

function onSelect(action) {
	if (action.disabled) return
	emit("select", action.key ?? action.label)
}
</script>
