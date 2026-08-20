<!--
  GModal — modal / bottom sheet (spec §10.3 #25). Bottom sheet on mobile,
  centred dialog at lg: (§20.7 #25).

  THE FOCUS-TRAP WORKAROUND IS PRESERVED VERBATIM from CustomIonModal.vue and
  must stay. ion-modal traps focus inside itself, which makes an autocomplete
  or any portalled control unusable within it —
  https://github.com/ionic-team/ionic-framework/issues/24646
  The fix: initial-breakpoint / breakpoints / backdrop-breakpoint=1 disable
  Ionic's own backdrop, and a plain div backdrop is rendered instead. Every one
  of those four props is load-bearing. Do not "simplify" this — the bug is
  real, it is upstream, and it is still open.

  Only the SKIN is new, applied through ion-modal's published CSS custom
  properties (§16.3): --background, --border-radius, --box-shadow, and the
  lg: width/height. The surface is SOLID (--glass-fill-fallback), not glass:
  a modal always covers page content that is itself glass, and glass over
  glass is nested glass (§15).

  Props (CustomIonModal's API, unchanged so phase 5 can swap the import):
    trigger  string — id of the element that opens the modal
    isOpen   boolean — controlled open state
    title    string — optional heading rendered above the slot
  Emits:
    did-dismiss  — Ionic's didDismiss, as before
    did-present  — Ionic's didPresent. Forwarded because content that starts a
                   camera or initialises a map needs it; swallowing it would
                   force callers back onto a raw ion-modal
    will-dismiss — Ionic's willDismiss, for teardown
  Slots:
    default / actionSheet — content. `actionSheet` is kept as an alias so
    existing call sites keep working through the phase 5 swap.
-->
<template>
	<ion-modal
		ref="modal"
		class="g-modal"
		:trigger="trigger"
		:initial-breakpoint="1"
		:breakpoints="[0, 1]"
		:backdrop-breakpoint="1"
		:is-open="isOpen"
		@willPresent="showModalBackdrop = true"
		@willDismiss="onWillDismiss"
		@didPresent="() => emit('did-present')"
		@didDismiss="() => emit('did-dismiss')"
	>
		<div class="g-sheet" role="dialog" :aria-label="title || undefined">
			<p v-if="title" class="g-sheet__title">{{ title }}</p>
			<slot name="actionSheet" />
			<slot />
		</div>
	</ion-modal>

	<!-- backdrop — hand-built because backdrop-breakpoint=1 disables Ionic's -->
	<div
		v-if="showModalBackdrop"
		class="g-scrim"
		aria-hidden="true"
		@click="() => modalController.dismiss()"
	></div>
</template>

<script setup>
import { ref } from "vue"
import { IonModal, modalController } from "@ionic/vue"

defineProps({
	trigger: { type: String, required: false },
	isOpen: { type: Boolean, required: false },
	title: { type: String, default: "" },
})
const emit = defineEmits(["did-dismiss", "did-present", "will-dismiss"])

function onWillDismiss(event) {
	showModalBackdrop.value = false
	emit("will-dismiss", event)
}
const showModalBackdrop = ref(false)
</script>
