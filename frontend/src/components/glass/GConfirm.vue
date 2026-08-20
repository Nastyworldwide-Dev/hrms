<!--
  GConfirm — a confirmation dialog. Not a new primitive: it is GModal (§10.3
  #25) plus two GButtons, composed once instead of five times.

  It exists because the five frappe-ui `Dialog` call sites this replaces are
  all the same shape — title, a sentence, cancel + confirm — and copying that
  markup into five views is exactly the duplication the component library is
  meant to prevent. Presentation, focus-trap workaround and the lg: centring
  all come from GModal.

  Props:
    isOpen       boolean — controlled open state
    title        string, required — what is about to happen, e.g. "Delete leave application"
    confirmLabel string, default "Confirm"
    cancelLabel  string, default "Cancel"
    destructive  boolean — the confirm action deletes or cancels something
    pending      boolean — §11.4: the server has been asked and has not answered
  Emits:
    confirm      — the confirm action was taken
    cancel       — dismissed, by button, backdrop or escape. Wire this to close.
  Slot: default — the body sentence. §11.3's copy rules apply: say what will
        happen, never apologise, never surface a system term.
-->
<template>
	<GModal :is-open="isOpen" :title="title" @did-dismiss="$emit('cancel')">
		<p class="g-confirm__body">
			<slot />
		</p>

		<div class="g-confirm__actions">
			<GGhostButton :label="cancelLabel" @click="$emit('cancel')" />
			<GButton
				:label="confirmLabel"
				:pending="pending"
				:class="destructive ? 'g-confirm__destructive' : undefined"
				@click="$emit('confirm')"
			/>
		</div>
	</GModal>
</template>

<script setup>
import GModal from "./GModal.vue"
import GButton from "./GButton.vue"
import GGhostButton from "./GGhostButton.vue"

defineProps({
	isOpen: { type: Boolean, default: false },
	title: { type: String, required: true },
	confirmLabel: { type: String, default: "Confirm" },
	cancelLabel: { type: String, default: "Cancel" },
	destructive: { type: Boolean, default: false },
	pending: { type: Boolean, default: false },
})
defineEmits(["confirm", "cancel"])
</script>
