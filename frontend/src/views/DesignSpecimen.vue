<!--
  /design — Glass specimen route (spec §16.4). Dev bundle only; registered
  behind import.meta.env.DEV in router/index.js. Every Glass component in
  every state; theme + reduce-transparency toggles. Each phase-2 prompt
  appends its components here.
-->
<template>
	<ion-page>
		<ion-content>
			<div class="spec">
				<div class="spec__field" aria-hidden="true" />

				<header class="spec__head">
					<h1 class="spec__title">Glass specimens</h1>
					<div class="spec__toggles">
						<GGhostButton
							:label="`Theme: ${resolved}`"
							@click="setTheme(resolved === 'dark' ? 'light' : 'dark', $event)"
						/>
						<GGhostButton
							:label="`Transparency: ${transparency.reduce ? 'reduced' : 'full'}`"
							@click="setTransparency(!transparency.reduce)"
						/>
					</div>
				</header>

				<section class="spec__section">
					<h2 class="spec__label">RECIPE — panel + ghost surfaces (§6)</h2>
					<div class="g-glass spec__panel">Panel glass — blur 20px</div>
					<div class="g-glass-ghost spec__panel">Ghost glass — blur 18px</div>
				</section>

				<section class="spec__section">
					<h2 class="spec__label">GBUTTON (§10.1 #1 · §11.4)</h2>
					<GButton label="CHECK IN" @click="log('GButton')" />
					<GButton label="CHECK IN" pending-label="Checking in…" pending />
					<GButton label="CHECK IN" disabled />
				</section>

				<section class="spec__section">
					<h2 class="spec__label">GGHOSTBUTTON (§10.1 #2)</h2>
					<GGhostButton label="VIEW FULL CALENDAR" @click="log('GGhostButton')" />
					<GGhostButton label="VIEW FULL CALENDAR" disabled />
				</section>

				<section class="spec__section">
					<h2 class="spec__label">GBADGE (§10.1 #7)</h2>
					<div class="spec__row">
						<GBadge variant="open">Open</GBadge>
						<GBadge variant="resolved">Resolved</GBadge>
					</div>
				</section>

				<section class="spec__section">
					<h2 class="spec__label">GSTATUSCHIP (§10.3 #28 — proposal)</h2>
					<div class="spec__row">
						<GStatusChip v-for="s in statuses" :key="s" :status="s" />
					</div>
				</section>

				<section class="spec__section">
					<h2 class="spec__label">GEMPTYSTATE (§11.1)</h2>
					<GEmptyState
						title="No leave taken this year"
						body="Your applications will appear here once submitted"
					/>
				</section>

				<section class="spec__section">
					<h2 class="spec__label">GSKELETON (§11.2)</h2>
					<div class="g-glass spec__panel">
						<GSkeleton width="42%" height="10px" />
						<GSkeleton height="31px" radius="var(--g-radius-well)" />
						<GSkeleton width="68%" height="10px" />
					</div>
				</section>

				<section class="spec__section">
					<h2 class="spec__label">GBANNER (§10.1 #10 · §11.3)</h2>
					<GBanner variant="info">Your shift window opens at 8:30 am.</GBanner>
					<GBanner variant="warning">You are offline. Your last check-in was saved.</GBanner>
					<GBanner variant="error">Check-in did not save. Tap to try again — do not punch twice.</GBanner>
				</section>

				<section class="spec__section">
					<h2 class="spec__label">GNOTEPANEL (§10.2 #22)</h2>
					<GNotePanel>OT eligible after 6:00 pm on working days. Claims close on the 25th.</GNotePanel>
				</section>
			</div>
		</ion-content>
	</ion-page>
</template>

<script setup>
import { computed } from "vue"
import { IonPage, IonContent } from "@ionic/vue"
import { theme, setTheme, resolvedTheme, transparency, setTransparency } from "@/data/theme"
import GButton from "@/components/glass/GButton.vue"
import GGhostButton from "@/components/glass/GGhostButton.vue"
import GBadge from "@/components/glass/GBadge.vue"
import GStatusChip from "@/components/glass/GStatusChip.vue"
import GEmptyState from "@/components/glass/GEmptyState.vue"
import GSkeleton from "@/components/glass/GSkeleton.vue"
import GBanner from "@/components/glass/GBanner.vue"
import GNotePanel from "@/components/glass/GNotePanel.vue"

const statuses = ["Draft", "Submitted", "Approved", "Rejected", "Cancelled"]
const resolved = computed(() => (theme.mode, resolvedTheme()))

function log(name) {
	console.info("[DesignSpecimen] click:", name)
}
</script>

<style scoped>
/* Specimen chrome only — tokens for every colour; layout values are local */
.spec {
	position: relative;
	min-height: 100%;
	padding: var(--g-screen-gutter);
	padding-bottom: 40px;
	background: var(--g-bg);
}
/* a static stand-in for the §3 light field so blur has something to show */
.spec__field {
	position: absolute;
	inset: 0;
	background:
		radial-gradient(280px 280px at 85% 8%, rgba(var(--g-brand-rgb) / 0.5), transparent 70%),
		radial-gradient(300px 300px at 8% 40%, rgba(var(--g-leave-rgb) / 0.35), transparent 70%);
	opacity: var(--g-blob-opacity);
	pointer-events: none;
}
.spec__head,
.spec__section {
	position: relative;
	margin-bottom: var(--g-stack-lg);
}
.spec__title {
	font-family: var(--g-type-screen-title-family);
	font-size: var(--g-type-screen-title-size);
	font-weight: var(--g-type-screen-title-weight);
	letter-spacing: var(--g-type-screen-title-tracking);
	color: var(--g-ink);
	margin-bottom: var(--g-stack-md);
}
.spec__label {
	font-family: var(--g-type-eyebrow-family);
	font-size: var(--g-type-eyebrow-size);
	font-weight: var(--g-type-eyebrow-weight);
	letter-spacing: var(--g-type-eyebrow-tracking);
	color: var(--g-ink2);
	margin-bottom: var(--g-stack-sm);
}
.spec__section > * + * {
	margin-top: var(--g-stack-sm);
}
.spec__toggles {
	display: flex;
	gap: var(--g-stack-sm);
}
.spec__panel {
	padding: var(--g-pad-panel);
	color: var(--g-ink);
	font-family: var(--g-type-card-title-family);
	font-size: var(--g-type-card-title-size);
	font-weight: var(--g-type-card-title-weight);
}
.spec__panel > * + * {
	margin-top: 9px;
}
.spec__row {
	display: flex;
	flex-wrap: wrap;
	gap: var(--g-stack-sm);
	align-items: center;
}
</style>
