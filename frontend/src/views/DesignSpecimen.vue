<!--
  /design — Glass specimen route (spec §16.4). Dev bundle only; registered
  behind import.meta.env.DEV in router/index.js. Every Glass component in
  every state; theme + reduce-transparency toggles. Each phase-2 prompt
  appends its components here.
-->
<template>
	<ion-page>
		<ion-content>
			<GPullRefresh @refresh="onRefresh" />

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

				<h2 class="spec__title">Tier B</h2>

				<section class="spec__section">
					<h2 class="spec__label">GLISTPANEL + GLISTROW (§10.1 #3) — one surface</h2>
					<GListPanel>
						<GListRow label="Apply for leave" @click="log('row')">
							<template #icon>&rarr;</template>
						</GListRow>
						<GListRow label="Claim overtime" sublabel="Closes on the 25th" />
						<GListRow label="Payslip" amount="RM 4,250.00" />
						<GListRow label="Report an issue">
							<template #badge><GBadge variant="open">Open</GBadge></template>
						</GListRow>
						<GListRow label="Sign out" destructive :chevron="false" />
					</GListPanel>
				</section>

				<section class="spec__section">
					<h2 class="spec__label">GLISTPANEL — loading (§11.2) and empty (§11.1)</h2>
					<GListPanel loading />
					<GListPanel empty>
						<template #empty>
							<GEmptyState
								title="Nothing reported"
								body="If something looks wrong, tell us — a screenshot helps"
							/>
						</template>
					</GListPanel>
				</section>

				<section class="spec__section">
					<h2 class="spec__label">GINPUT / GTEXTAREA (§10.1 #4, #5)</h2>
					<GInput v-model="form.date" label="Date worked" placeholder="20 August 2026" />
					<GInput v-model="form.hours" label="Hours" error="You have 2.5 days available and applied for 3." />
					<GInput v-model="form.locked" label="Approver" disabled />
					<GTextarea v-model="form.reason" label="Explanation" placeholder="What did you work on?" />
				</section>

				<section class="spec__section">
					<h2 class="spec__label">GBALANCEGRID + GBALANCECARD (§15.2) — 2-up, 4-up at lg:</h2>
					<GBalanceGrid>
						<GBalanceCard label="Annual leave" :remaining="7.5" :allocated="8" />
						<GBalanceCard label="Medical" :remaining="12" :allocated="14" :prorated-percentage="22" />
						<GBalanceCard label="Replacement" :remaining="1" :allocated="4" />
						<GBalanceCard label="Unpaid" :remaining="0" :allocated="0" />
					</GBalanceGrid>
				</section>

				<section class="spec__section">
					<h2 class="spec__label">GBALANCEGRID — loading and empty</h2>
					<GBalanceGrid loading />
					<GBalanceGrid empty>
						<template #empty>
							<GEmptyState
								title="No leave allocated yet"
								body="People &amp; Culture are setting this up. Check back shortly."
							/>
						</template>
					</GBalanceGrid>
				</section>

				<section class="spec__section">
					<h2 class="spec__label">GSTATPANEL + GSTATTILE (§10.2 #13) — one surface</h2>
					<GStatPanel>
						<GStatTile :value="10" label="Present" />
						<GStatTile :value="2" label="Leave" />
						<GStatTile :value="1" label="Absent" />
					</GStatPanel>
					<GStatPanel loading />
				</section>

				<section class="spec__section">
					<h2 class="spec__label">GISSUECARD (§10.2 #14)</h2>
					<GIssueCard
						issue-id="HR-2026-0043"
						title="Payslip shows the wrong shift allowance"
						meta="Reported 2 days ago"
						@click="log('GIssueCard')"
					>
						<template #badge><GBadge variant="open">Open</GBadge></template>
					</GIssueCard>
					<GIssueCard
						issue-id="HR-2026-0031"
						title="Check-in did not register at the Klang site"
						meta="Resolved 20 August 2026"
					>
						<template #badge><GBadge variant="resolved">Resolved</GBadge></template>
					</GIssueCard>
				</section>

				<section class="spec__section">
					<h2 class="spec__label">GPROGRESSRING (§10.1 #9)</h2>
					<div class="spec__row">
						<GProgressRing :score="4.2" />
						<GProgressRing :score="0" />
						<GProgressRing :score="5" />
						<GProgressRing :score="0" loading />
					</div>
				</section>

				<h2 class="spec__title">Tier C</h2>

				<section class="spec__section">
					<h2 class="spec__label">GCALENDAR (§10.2 #18) — legend labels every state</h2>
					<GCalendar title="August 2026" :days="calendarDays" :leading-blanks="4" @select="log('day')" />
				</section>

				<section class="spec__section">
					<h2 class="spec__label">GSCOREPANEL (§10.2 #15)</h2>
					<GScorePanel :score="4.2" verdict="Exceeds expectations" cycle="H1 2026 review" />
					<GScorePanel :score="0" verdict="" loading />
				</section>

				<section class="spec__section">
					<h2 class="spec__label">GKRAPANEL (§10.2 #16) — track solid per §6.3</h2>
					<GKraPanel :rows="kraRows" />
					<GKraPanel loading />
				</section>

				<section class="spec__section">
					<h2 class="spec__label">GGOALSPANEL (§10.2 #17)</h2>
					<GGoalsPanel :count="4" label="Goals in progress" sublabel="2 due this month" @click="log('GGoalsPanel')" />
				</section>

				<section class="spec__section">
					<h2 class="spec__label">GMAPPANEL (§10.2 #19) — gradient body, glass caption chip</h2>
					<GMapPanel caption="3.1390° N, 101.6869° E" />
					<GMapPanel loading />
				</section>

				<section class="spec__section">
					<h2 class="spec__label">GSELFIEPANEL (§10.2 #20)</h2>
					<GSelfiePanel @click="log('GSelfiePanel')" />
					<GSelfiePanel loading />
				</section>

				<section class="spec__section">
					<h2 class="spec__label">GCLOCK (§10.2 #21) — seconds decorative, aria-hidden</h2>
					<GClock time="6:17" seconds="42" suffix="pm" />
					<GClock time="9:05" />
				</section>

				<section class="spec__section">
					<h2 class="spec__label">GLOGOWELL (§10.2 #23)</h2>
					<div class="spec__row">
						<GLogoWell label="Frappe HR" />
						<GLogoWell mark="NZ" />
					</div>
				</section>

				<section class="spec__section">
					<h2 class="spec__label">GAPPHEADER (§10.3 #24) — avatar hides at lg:, kicker appears</h2>
					<GAppHeader
						title="My KPI"
						:unread="3"
						kicker="Wednesday, 20 August"
						avatar-label="Siti Rahman"
						@notifications="log('notifications')"
						@profile="log('profile')"
					/>
					<GAppHeader title="Attendance" avatar-label="Siti Rahman" />
				</section>

				<section class="spec__section">
					<h2 class="spec__label">GSEGMENTED (§10.3) — TabButtons API</h2>
					<GSegmented v-model="segment" :buttons="segments" label="Request type" />
					<p class="spec__note">selected: {{ segment }}</p>
				</section>

				<h2 class="spec__title">Tier D</h2>

				<section class="spec__section">
					<h2 class="spec__label">GMODAL / GACTIONSHEET (§10.3 #25, #26) — focus-trap workaround preserved</h2>
					<GButton label="OPEN ACTION SHEET" @click="sheetOpen = true" />
					<GActionSheet
						:is-open="sheetOpen"
						title="Leave application"
						:actions="sheetActions"
						@select="onSheetSelect"
						@did-dismiss="sheetOpen = false"
					/>
					<p class="spec__note">last action: {{ lastAction || "none" }}</p>
				</section>

				<section class="spec__section">
					<h2 class="spec__label">GTOAST (§10.3 #27) — wraps frappe-ui toast</h2>
					<div class="spec__row">
						<GGhostButton label="SUCCESS" @click="gToast({ title: 'Leave applied', text: 'Your manager has been notified.', variant: 'success' })" />
						<GGhostButton label="ERROR" @click="gToast({ title: 'Check-in did not save', text: 'Tap to try again — do not punch twice.', variant: 'error' })" />
					</div>
				</section>

				<section class="spec__section">
					<h2 class="spec__label">GSEARCHBAR (§10.3)</h2>
					<GSearchBar v-model="search" placeholder="Search requests" />
					<p class="spec__note">query: {{ search || "empty" }}</p>
				</section>

				<section class="spec__section">
					<h2 class="spec__label">GAVATAR (§10.3) — rounding returns, .m-avatar-sq not ported</h2>
					<div class="spec__row">
						<GAvatar label="Siti Rahman" />
						<GAvatar label="Siti Rahman" round />
						<GAvatar label="Ahmad" :size="56" />
						<GAvatar image="/broken-path.png" label="Fallback" />
					</div>
				</section>

				<section class="spec__section">
					<h2 class="spec__label">GDATATABLE (§10.3 · §6.3) — solid, never glass</h2>
					<GDataTable :columns="payslipColumns" :rows="payslipRows" caption="August 2026 payslip" />
					<GDataTable :columns="payslipColumns" loading />
					<GDataTable :columns="payslipColumns" :rows="[]">
						<template #empty>
							<GEmptyState
								title="No payslips available"
								body="Your first payslip appears after your first full pay cycle"
							/>
						</template>
					</GDataTable>
				</section>

				<section class="spec__section">
					<h2 class="spec__label">GFILEUPLOAD (§10.3)</h2>
					<GFileUpload :model-value="files" @preview="log('preview')" @remove="log('remove')" />
					<GFileUpload :model-value="[]" uploading />
				</section>

				<section class="spec__section">
					<h2 class="spec__label">GLINKPICKER / GDATEPICKER (§10.3) — frappe-ui 0.1.105</h2>
					<GLinkPicker v-model="link" :options="linkOptions" label="Approver" placeholder="Search employees" />
					<GDatePicker v-model="date" label="Date worked" placeholder="Select a date" />
				</section>

				<section class="spec__section">
					<h2 class="spec__label">GMODAL (§10.3 #25) — bottom sheet, centred at lg:</h2>
					<GButton label="OPEN MODAL" @click="modalOpen = true" />
					<GModal :is-open="modalOpen" title="Delete attachment" @did-dismiss="modalOpen = false">
						<p class="spec__note">
							Ionic's focus trap is worked around here exactly as CustomIonModal does it —
							an autocomplete inside this sheet stays usable.
						</p>
						<GLinkPicker v-model="link" :options="linkOptions" label="Reassign to" />
					</GModal>
				</section>

				<section class="spec__section">
					<h2 class="spec__label">GPULLREFRESH (§10.3) — mounted on this page; pull down to see it</h2>
					<p class="spec__note">
						The live refresher sits at the top of this ion-content. Its Ionic spinner is switched off
						(§11.2); the indicator below is the same markup it renders.
					</p>
					<div class="g-refresh">
						<span class="g-refresh__bar" aria-hidden="true"><span class="g-refresh__fill" /></span>
						Pull to refresh
					</div>
				</section>
			</div>
		</ion-content>
	</ion-page>
</template>

<script setup>
import { computed, reactive, ref } from "vue"
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
import GListPanel from "@/components/glass/GListPanel.vue"
import GListRow from "@/components/glass/GListRow.vue"
import GInput from "@/components/glass/GInput.vue"
import GTextarea from "@/components/glass/GTextarea.vue"
import GBalanceGrid from "@/components/glass/GBalanceGrid.vue"
import GBalanceCard from "@/components/glass/GBalanceCard.vue"
import GStatPanel from "@/components/glass/GStatPanel.vue"
import GStatTile from "@/components/glass/GStatTile.vue"
import GIssueCard from "@/components/glass/GIssueCard.vue"
import GProgressRing from "@/components/glass/GProgressRing.vue"
import GCalendar from "@/components/glass/GCalendar.vue"
import GScorePanel from "@/components/glass/GScorePanel.vue"
import GKraPanel from "@/components/glass/GKraPanel.vue"
import GGoalsPanel from "@/components/glass/GGoalsPanel.vue"
import GMapPanel from "@/components/glass/GMapPanel.vue"
import GSelfiePanel from "@/components/glass/GSelfiePanel.vue"
import GClock from "@/components/glass/GClock.vue"
import GLogoWell from "@/components/glass/GLogoWell.vue"
import GAppHeader from "@/components/glass/GAppHeader.vue"
import GSegmented from "@/components/glass/GSegmented.vue"
import GModal from "@/components/glass/GModal.vue"
import GActionSheet from "@/components/glass/GActionSheet.vue"
import GSearchBar from "@/components/glass/GSearchBar.vue"
import GAvatar from "@/components/glass/GAvatar.vue"
import GDataTable from "@/components/glass/GDataTable.vue"
import GFileUpload from "@/components/glass/GFileUpload.vue"
import GLinkPicker from "@/components/glass/GLinkPicker.vue"
import GDatePicker from "@/components/glass/GDatePicker.vue"
import GPullRefresh from "@/components/glass/GPullRefresh.vue"
import { gToast } from "@/components/glass/toast"

const statuses = ["Draft", "Submitted", "Approved", "Rejected", "Cancelled"]
const form = reactive({ date: "", hours: "3", locked: "Siti Rahman", reason: "" })
const segment = ref("all")
const segments = [
	{ key: "all", label: "All" },
	{ key: "mine", label: "Mine" },
	{ key: "team", label: "Team" },
]
const kraRows = [
	{ label: "Data accuracy", weight: "30%", score: 4.5, max: 5 },
	{ label: "Response time", weight: "25%", score: 3.8, max: 5 },
	{ label: "Team collaboration", weight: "25%", score: 4.2, max: 5 },
	{ label: "Process adherence", weight: "20%", score: 4.0, max: 5 },
]
const sheetOpen = ref(false)
const modalOpen = ref(false)
const lastAction = ref("")

function onRefresh(event) {
	console.info("[DesignSpecimen] pull-to-refresh")
	setTimeout(() => event.target.complete(), 900)
}
const sheetActions = [
	{ key: "approve", label: "Approve" },
	{ key: "open", label: "Open full form" },
	{ key: "cancel", label: "Cancel request", destructive: true },
	{ key: "locked", label: "Delete (not permitted)", disabled: true },
]
function onSheetSelect(key) {
	lastAction.value = key
	sheetOpen.value = false
}
const search = ref("")
const link = ref(null)
const date = ref("")
const linkOptions = [
	{ label: "Siti Rahman", value: "HR-EMP-0001" },
	{ label: "Ahmad Faiz", value: "HR-EMP-0002" },
]
const files = [{ file_name: "receipt-august.pdf" }, { file_name: "medical-cert.jpg" }]
const payslipColumns = [
	{ key: "item", label: "Item" },
	{ key: "amount", label: "Amount", numeric: true },
]
const payslipRows = [
	{ item: "Basic salary", amount: "4,000.00" },
	{ item: "Shift allowance", amount: "250.00" },
	{ item: "EPF employee", amount: "−440.00" },
	{ item: "Net pay", amount: "3,810.00", total: true },
]
// one month of mixed states so every calendar treatment is on screen at once
const calendarDays = Array.from({ length: 31 }, (_, i) => {
	const day = i + 1
	const weekday = (i + 4) % 7
	let state = "present"
	if (weekday >= 5) state = "rest"
	else if (day === 12 || day === 13) state = "leave"
	else if (day === 19) state = "absent"
	else if (day > 20) state = "none"
	return { day, state }
})
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
.spec__note {
	font-family: var(--g-type-caption-family);
	font-size: var(--g-type-caption-size);
	color: var(--g-ink2);
}
</style>
