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
		@willPresent="onWillPresent"
		@willDismiss="onWillDismiss"
		@didPresent="onDidPresent"
		@didDismiss="onDidDismiss"
	>
		<div class="g-sheet" role="dialog" aria-modal="true" :aria-label="title || undefined">
			<p v-if="title" class="g-sheet__title">{{ title }}</p>
			<slot name="actionSheet" />
			<slot />
		</div>
	</ion-modal>

	<!-- backdrop — hand-built because backdrop-breakpoint=1 disables Ionic's.
	     Teleported to body: inside the page it was clipped to the page's own
	     box, so on desktop the side nav stayed bright and clickable under an
	     open sheet (audit APP-14). -->
	<Teleport to="body">
		<div v-if="showModalBackdrop" class="g-scrim" aria-hidden="true" @click="closeOwnSheet"></div>
	</Teleport>
</template>

<script setup>
import { onBeforeUnmount, ref } from "vue"
import { useRoute } from "vue-router"
import { IonModal } from "@ionic/vue"

import { holdPageInert, releasePageInert } from "@/utils/sheetInert"

defineProps({
	trigger: { type: String, required: false },
	isOpen: { type: Boolean, required: false },
	title: { type: String, default: "" },
})
const emit = defineEmits(["did-dismiss", "did-present", "will-dismiss"])

const modal = ref(null)
const route = useRoute()
//: The path the sheet was opened on. The router guard closes PRESENTED sheets
//: before a navigation lands, but a sheet still animating in is not presented
//: yet — Back pressed mid-animation let it finish opening over the next page
//: (audit P0-3). A sheet that lands on a different page closes itself.
let openedOn = null
const showModalBackdrop = ref(false)
//: The page THIS sheet froze — the node itself, so release frees that page even
//: after the route moved on. A sheet can be torn down (route change, v-if)
//: without Ionic's dismiss events, and no page may stay frozen behind a sheet
//: that no longer exists.
let frozenPage = null
//: The control that opened the sheet, so focus returns to it on close
//: (WAI-ARIA dialog pattern: focus moves in, stays in, and comes back).
let opener = null

//: The page the user is looking at — the one the sheet covers. Ionic marks the
//: others .ion-page-hidden, and the sheet itself lives at the app root.
function visiblePage() {
	return document.querySelector("ion-router-outlet .ion-page:not(.ion-page-hidden)")
}

function onWillPresent() {
	openedOn = route.path
	showModalBackdrop.value = true
	opener = document.activeElement
	if (!frozenPage) frozenPage = holdPageInert(visiblePage)
}

function onDidPresent() {
	if (openedOn && route.path !== openedOn) {
		console.info("[GModal] opened on", openedOn, "but landed on", route.path, "- closing")
		closeOwnSheet()
		return
	}
	moveFocusIn()
	emit("did-present")
}

function moveFocusIn() {
	const sheet = modal.value?.$el?.querySelector(".g-sheet")
	if (!sheet || sheet.contains(document.activeElement)) return
	sheet.setAttribute("tabindex", "-1")
	sheet.focus({ preventScroll: true })
}

function onWillDismiss(event) {
	showModalBackdrop.value = false
	emit("will-dismiss", event)
}

function onDidDismiss() {
	showModalBackdrop.value = false
	release()
	if (opener?.isConnected) opener.focus?.({ preventScroll: true })
	opener = null
	emit("did-dismiss")
}

function release() {
	releasePageInert(frozenPage)
	frozenPage = null
}

//: The scrim closes ITS sheet. `modalController.dismiss()` closed whichever
//: overlay was on top — another sheet, or nothing while this one was still
//: animating in (audit APP-2).
function closeOwnSheet() {
	console.info("[GModal] scrim tapped, closing this sheet")
	modal.value?.$el?.dismiss?.()
}

onBeforeUnmount(() => {
	showModalBackdrop.value = false
	release()
})
</script>
