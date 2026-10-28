<template>
	<GPage>
		<ShellHeader :title="__('Organizational Chart')">
			<template #actions>
				<button v-if="!isSearching && !isOnSelf" class="oc-you" @click="goToSelf">
					<LocateFixed class="h-4 w-4" />
					<span>{{ __("You") }}</span>
				</button>
			</template>
		</ShellHeader>
		<ion-content class="ion-padding g-page__content">
			<div class="w-full max-w-content-column-lg mx-auto px-4">
				<div class="flex flex-col gap-3 mb-6">
					<GSearchBar
						v-model="searchQuery"
						:placeholder="__('Search by name')"
						:label="__('Search by name')"
					/>
				</div>

				<!-- Loading state -->
				<div
					v-if="nodeData.loading"
					class="oc-loading"
					role="status"
					:aria-label="__('Loading the organizational chart')"
				>
					<div class="oc-flow">
						<GSkeleton width="100%" height="56px" radius="18px" class="oc-sk-box" />
						<span class="oc-line" aria-hidden="true"></span>
						<GSkeleton width="100%" height="190px" radius="20px" class="oc-sk-focus" />
						<span class="oc-line" aria-hidden="true"></span>
						<div class="oc-kids">
							<GSkeleton v-for="i in 4" :key="i" width="100%" height="110px" radius="18px" />
						</div>
					</div>
				</div>

				<!-- Error state, also when the request never produced a person -->
				<div v-else-if="nodeData.error || !person" class="g-empty">
					<TriangleAlert class="w-12 h-12 oc-warn-icon" />
					<h2 class="g-empty__title">{{ __("Could not load the chart") }}</h2>
					<p class="g-empty__body">{{ __("Check your connection, then try again.") }}</p>
					<GButton class="oc-retry" :label="__('Retry')" @click="retryFetch" />
				</div>

				<!-- Loaded content -->
				<template v-else>
					<!-- Search results -->
					<template v-if="isSearching">
						<section v-if="searchResults.length" class="oc-sec">
							<h2 class="oc-sec__title" role="status">
								{{ searchResults.length }}
								{{ searchResults.length === 1 ? __("match") : __("matches") }}
							</h2>
							<div class="g-form-group">
								<button
									v-for="p in searchResults"
									:key="p.id"
									class="g-row g-row--tappable"
									@click="focusPerson(p.id)"
								>
									<GAvatar :image="p.image" :label="p.name" round badge />
									<span class="g-row__body">
										<span class="g-row__label">{{ p.name }}</span>
										<span class="g-row__sub">{{ subline(p) }}</span>
									</span>
								</button>
							</div>
						</section>
						<div v-else class="g-empty" role="status">
							<Search class="w-12 h-12 text-ink-3" />
							<h2 class="g-empty__title">{{ __("No one found") }}</h2>
							<p class="g-empty__body">
								{{ __('Nobody called "{0}" in this view.', [searchQuery.trim()]) }}
							</p>
						</div>
					</template>

					<!-- Normal view -->
					<template v-else>
						<!-- HR gaps section -->
						<section v-if="isHR && gaps.total > 0" class="oc-sec">
							<div class="g-form-group">
								<button
									class="g-row g-row--tappable"
									:aria-expanded="gapsExpanded"
									aria-controls="oc-gaps-detail"
									@click="gapsExpanded = !gapsExpanded"
								>
									<span class="g-row__well oc-well-warn">
										<TriangleAlert class="w-4 h-4" />
									</span>
									<span class="g-row__body">
										<span class="g-row__label oc-wrap">{{ gapsMessage }}</span>
									</span>
									<ChevronDown class="g-row__chevron oc-chev" />
								</button>
								<div v-if="gapsExpanded" id="oc-gaps-detail">
									<template v-for="grp in gapGroups" :key="grp.key">
										<div v-if="grp.rows.length" class="oc-gap-h">
											{{ grp.title }} · {{ grp.rows.length }}
										</div>
										<div v-for="item in grp.rows" :key="item.id" class="g-row">
											<span class="g-row__body">
												<span class="g-row__label">{{ item.name }}</span>
												<span class="g-row__sub">{{ gapSub(item) }}</span>
											</span>
											<a
												:href="desktopLink(item.id)"
												target="_self"
												class="oc-link"
												:aria-label="__('Fix {0} in Desk', [item.name])"
											>
												{{ __("Fix in Desk") }}
												<ExternalLink class="w-3.5 h-3.5" aria-hidden="true" />
											</a>
										</div>
									</template>
								</div>
							</div>
						</section>

						<!-- The chart: managers, then the person, then their team, joined by lines -->
						<div class="oc-flow">
							<!-- Managers above the direct one fold into one pill, top first -->
							<template v-if="ladder.above.length">
								<button
									class="oc-node oc-node--pill"
									:aria-expanded="aboveExpanded"
									aria-controls="oc-above-list"
									@click="aboveExpanded = !aboveExpanded"
								>
									<span v-if="!aboveExpanded" class="oc-stack" aria-hidden="true">
										<GAvatar
											v-for="p in ladder.above.slice(-3)"
											:key="p.id || p.name"
											:image="p.image"
											:label="p.name"
											:size="24"
											round
											badge
											decorative
										/>
									</span>
									<span class="oc-pill__label">
										{{
											aboveExpanded
												? __("Hide higher managers")
												: __("{0} more above", [ladder.above.length])
										}}
									</span>
									<ChevronDown class="oc-chev" />
								</button>
								<span class="oc-line" aria-hidden="true"></span>
								<div v-if="aboveExpanded" id="oc-above-list" class="oc-flow">
									<template v-for="p in ladder.above" :key="p.id || p.name">
										<button class="oc-node" :disabled="!!p.message" @click="focusPerson(p.id)">
											<GAvatar v-if="!p.message" :image="p.image" :label="p.name" round badge />
											<span v-else class="g-row__well oc-well-warn">
												<UserRoundX class="w-4 h-4" />
											</span>
											<span class="oc-node__body">
												<span class="oc-node__name">{{
													p.message ? __("Manager has left") : p.name
												}}</span>
												<span class="oc-node__sub">{{ p.designation }}</span>
											</span>
										</button>
										<span class="oc-line" aria-hidden="true"></span>
									</template>
								</div>
							</template>

							<!-- Direct manager -->
							<template v-if="ladder.direct">
								<div v-if="ladder.direct.message" class="oc-node oc-node--static">
									<span class="g-row__well oc-well-warn">
										<UserRoundX class="w-4 h-4" />
									</span>
									<span class="oc-node__body">
										<span class="oc-node__eyebrow">{{ __("Direct manager") }}</span>
										<span class="oc-node__name">{{ __("Manager has left") }}</span>
										<span class="oc-node__sub oc-wrap">
											{{ __("HR sets a new manager in Desk") }}
										</span>
									</span>
								</div>
								<button v-else class="oc-node" @click="focusPerson(ladder.direct.id)">
									<GAvatar :image="ladder.direct.image" :label="ladder.direct.name" round badge />
									<span class="oc-node__body">
										<span class="oc-node__eyebrow">{{ __("Direct manager") }}</span>
										<span class="oc-node__name">{{ ladder.direct.name }}</span>
										<span class="oc-node__sub">
											{{ ladder.direct.designation }}
											<template v-if="ladder.direct.away">
												· <span class="oc-away">{{ __("Away today") }}</span>
											</template>
										</span>
									</span>
								</button>
								<span class="oc-line" aria-hidden="true"></span>
							</template>
							<template v-else>
								<div class="oc-node oc-node--static">
									<span class="g-row__well oc-well-warn">
										<Network class="w-4 h-4" />
									</span>
									<span class="oc-node__body">
										<span class="oc-node__name">{{ __("No manager set yet") }}</span>
										<span class="oc-node__sub oc-wrap">{{ __("HR sets this in Desk.") }}</span>
									</span>
								</div>
								<span class="oc-line oc-line--dash" aria-hidden="true"></span>
							</template>

							<!-- The person in focus -->
							<section
								ref="focusCard"
								class="oc-node oc-node--focus"
								tabindex="-1"
								:aria-label="person.name"
							>
								<GAvatar :size="64" round badge :image="person.image" :label="person.name" />
								<h2 class="oc-focus__name">{{ person.name }}</h2>
								<p class="oc-focus__designation">{{ person.designation }}</p>
								<p class="oc-focus__meta">{{ subline(person) }}</p>
								<p v-if="isHR" class="oc-focus__meta">{{ person.company }}</p>
								<div v-if="person.id === userId || person.away" class="oc-focus__chips">
									<span v-if="person.id === userId" class="oc-chip">{{ __("This is you") }}</span>
									<span v-if="person.away" class="oc-chip oc-chip--away">{{
										__("Away today")
									}}</span>
								</div>
							</section>

							<!-- Their team: boxes hung off one line, two to a row -->
							<template v-if="teamDisplay.all.length">
								<span class="oc-line" aria-hidden="true"></span>
								<div
									id="oc-team-list"
									class="oc-kids"
									role="list"
									:aria-label="__('Team') + ' · ' + teamDisplay.all.length"
								>
									<button
										v-for="p in teamDisplay.shown"
										:key="p.id"
										class="oc-kid"
										role="listitem"
										@click="focusPerson(p.id)"
									>
										<span
											v-if="p.team_size"
											class="oc-count"
											:aria-label="__('Team of {0}', [p.team_size])"
										>
											<Users class="w-3 h-3" aria-hidden="true" />{{ p.team_size }}
										</span>
										<GAvatar :image="p.image" :label="p.name" round badge />
										<span class="oc-kid__name">{{ p.name }}</span>
										<span class="oc-kid__sub">{{ p.designation }}</span>
										<span v-if="p.away" class="oc-away">{{ __("Away today") }}</span>
									</button>
								</div>
								<button
									v-if="teamDisplay.more > 0 || teamExpanded"
									class="oc-node oc-node--pill oc-more"
									:aria-expanded="teamExpanded"
									aria-controls="oc-team-list"
									@click="teamExpanded = !teamExpanded"
								>
									<span class="oc-pill__label">
										{{
											teamExpanded ? __("Show fewer") : __("See all {0}", [teamDisplay.all.length])
										}}
									</span>
									<ChevronDown class="oc-chev" />
								</button>
								<p v-if="teamAwayCount > 0" class="oc-sec__aside oc-team-away">
									{{ __("{0} of {1} away today", [teamAwayCount, teamDisplay.all.length]) }}
								</p>
							</template>
							<template v-else>
								<span class="oc-line oc-line--dash" aria-hidden="true"></span>
								<div class="oc-node oc-node--ghost">{{ __("No team yet") }}</div>
							</template>
						</div>

						<!-- Same manager section (peers) -->
						<section v-if="peers.length > 0" class="oc-sec">
							<div class="g-form-group">
								<button
									class="g-row g-row--tappable"
									:aria-expanded="peersExpanded"
									aria-controls="oc-peers-list"
									@click="peersExpanded = !peersExpanded"
								>
									<span class="g-row__body">
										<span class="g-row__label">{{ __("Same manager") }} · {{ peers.length }}</span>
									</span>
									<ChevronDown class="g-row__chevron oc-chev" />
								</button>
								<div v-if="peersExpanded" id="oc-peers-list">
									<button
										v-for="p in peers"
										:key="p.id"
										class="g-row g-row--tappable"
										@click="focusPerson(p.id)"
									>
										<GAvatar :image="p.image" :label="p.name" round badge />
										<span class="g-row__body">
											<span class="g-row__label">{{ p.name }}</span>
											<span class="g-row__sub">{{ p.designation }}</span>
										</span>
									</button>
								</div>
							</div>
						</section>
					</template>
				</template>
			</div>
		</ion-content>
	</GPage>
</template>

<script setup>
import {
	TriangleAlert,
	ChevronDown,
	ExternalLink,
	LocateFixed,
	Network,
	Search,
	UserRoundX,
	Users,
} from "lucide-vue-next"
import { computed, inject, nextTick, ref, watch } from "vue"
import { useRouter, useRoute } from "vue-router"
import { IonContent } from "@ionic/vue"

import GPage from "@/components/glass/GPage.vue"
import GAvatar from "@/components/glass/GAvatar.vue"
import GButton from "@/components/glass/GButton.vue"
import GSkeleton from "@/components/glass/GSkeleton.vue"
import { gToast } from "@/components/glass/toast"
import GSearchBar from "@/components/glass/GSearchBar.vue"
import ShellHeader from "@/components/ShellHeader.vue"

import { createResource } from "frappe-ui"
import {
	subline,
	teamPreview,
	awayCount as countAway,
	chainRows as makeChainRows,
	chainLadder,
	gapsMessage as makeGapsMessage,
	gapSub,
} from "@/utils/orgChart"

const router = useRouter()
const route = useRoute()
const __ = inject("$translate")
const employee = inject("$employee")

const userId = computed(() => employee.data?.name)

// The focused employee lives in the URL (?employee=ID), so Back walks back.
// No query = the signed-in person (the server defaults to them).
const focusedId = computed(() => route.query.employee || "")

// Search and filter
const searchQuery = ref("")
const isSearching = computed(() => searchQuery.value.trim().length > 0)

// UI state
const teamExpanded = ref(false)
const peersExpanded = ref(false)
const aboveExpanded = ref(false)
const gapsExpanded = ref(false)
const focusCard = ref(null)

// Load the org chart node data (params are not reactive in frappe-ui: refetch on focus change)
const nodeData = createResource({
	url: "hrms.api.org_chart.get_node",
	method: "GET",
})
watch(focusedId, (id) => nodeData.submit(id ? { employee: id } : {}), { immediate: true })

// HR is told by the server: only HR receives data.gaps
const isHR = computed(() => nodeData.data?.gaps !== undefined)

// Compute current person
const person = computed(() => nodeData.data?.person)
const reports = computed(() => nodeData.data?.reports || [])

// Build chain up (reports to)
const chainRows = computed(() => {
	if (!nodeData.data || !nodeData.data.chain_up) return []
	const chain = nodeData.data.chain_up || []
	return makeChainRows(chain).map((entry) => ({
		...entry,
		name: entry.name || __("(no name)"),
	}))
})

// The chart's managers: direct one above the person, the rest folded, top first
const ladder = computed(() => chainLadder(chainRows.value))

// Team display with preview logic
const teamDisplay = computed(() => {
	const all = reports.value
	const preview = teamPreview(all, teamExpanded.value ? all.length : 4)
	return { shown: preview.shown, all, more: teamExpanded.value ? 0 : preview.more }
})

const teamAwayCount = computed(() => countAway(teamDisplay.value.all))

// Peers (same manager)
const peers = computed(() => nodeData.data?.peers || [])

// HR gaps
const gaps = computed(() => {
	if (!nodeData.data?.gaps) {
		return { total: 0, all: [], noManager: 0, leftManager: 0 }
	}
	const g = nodeData.data.gaps
	const all = (g.no_manager || []).concat(g.left_manager || [])
	return {
		total: all.length,
		all,
		noManager: (g.no_manager || []).length,
		leftManager: (g.left_manager || []).length,
	}
})

const gapsMessage = computed(() =>
	makeGapsMessage(__, person.value?.company, gaps.value.noManager, gaps.value.leftManager)
)

const gapGroups = computed(() => {
	const g = nodeData.data?.gaps || {}
	return [
		{ key: "none", title: __("No manager set"), rows: g.no_manager || [] },
		{ key: "left", title: __("Manager has left"), rows: g.left_manager || [] },
	]
})

// Search results
const searchResults = computed(() => {
	if (!isSearching.value) return []
	const q = searchQuery.value.trim().toLowerCase()
	const allPeople = [
		person.value,
		...(chainRows.value || []).filter((c) => c.id),
		...(teamDisplay.value.all || []),
		...(peers.value || []),
	].filter(Boolean)

	const unique = new Map()
	allPeople.forEach((p) => {
		if (!unique.has(p.id)) {
			unique.set(p.id, p)
		}
	})

	return Array.from(unique.values()).filter((p) => p.name.toLowerCase().includes(q))
})

// Helpers
function focusPerson(id) {
	if (!id) return
	router.push({ query: id === userId.value ? {} : { employee: id } })
	searchQuery.value = ""
	teamExpanded.value = false
	peersExpanded.value = false
	aboveExpanded.value = false
}

function goToSelf() {
	searchQuery.value = ""
	router.push({ query: {} })
}

const isOnSelf = computed(() => !focusedId.value || focusedId.value === userId.value)

async function retryFetch() {
	// The failure is shown by the error state itself; the catch only keeps the rejection from escaping.
	try {
		await nodeData.submit(focusedId.value ? { employee: focusedId.value } : {})
	} catch (e) {
		console.info("[OrgChart] retry failed", e)
	}
	if (nodeData.error) gToast({ title: __("Still could not load. Try again."), variant: "error" })
}

// A new person: bring the focus card into view for keyboard and screen-reader users.
watch(
	() => person.value?.id,
	async (id, old) => {
		if (!old || !id || id === old) return
		await nextTick()
		focusCard.value?.focus()
	},
	{ flush: "post" }
)

function desktopLink(id) {
	return `/desk/employee/${id}`
}
</script>

<style scoped>
.oc-you {
	display: inline-flex;
	align-items: center;
	gap: 6px;
	min-height: 44px;
	padding: 0 14px;
	border: 0;
	border-radius: 22px;
	background: var(--g-icon-bg);
	font-weight: 600;
}

.oc-sec {
	display: flex;
	flex-direction: column;
	gap: 8px;
	margin-bottom: 24px;
}
.oc-sec__head {
	display: flex;
	align-items: baseline;
	justify-content: space-between;
	gap: 8px;
	padding: 0 16px;
}
.oc-sec__title {
	margin: 0;
	font-size: 0.8125rem;
	line-height: 1.125rem;
	color: var(--g-ink2);
	font-weight: 400;
}
.oc-sec__aside {
	font-size: 0.8125rem;
	line-height: 1.125rem;
	color: var(--g-leave-ink);
	font-weight: 600;
}

.oc-wrap {
	white-space: normal;
	overflow-wrap: anywhere;
}
.oc-strong {
	font-weight: 600;
}
.oc-warn-icon {
	color: var(--g-warn-ink);
}
.oc-retry {
	margin-top: 20px;
}

.oc-chev {
	width: 16px;
	height: 16px;
	transition: transform var(--g-motion-state-change-duration) var(--g-motion-state-change-easing);
}
[aria-expanded="true"] > .oc-chev {
	transform: rotate(180deg);
}

.oc-well-warn {
	background: rgb(var(--g-warn-rgb) / 0.14);
	color: var(--g-warn-fill);
}

/* ---------- the flow chart ---------- */
/* Every box is outlined: ink in light (black), accent in dark (lime, set in
   glass-components.css). The person in focus gets the thicker line. */
.oc-flow {
	--oc-box-line: var(--g-ink);
	display: flex;
	flex-direction: column;
	align-items: center;
	margin-bottom: 24px;
}
.oc-line {
	width: 2px;
	height: 20px;
	flex: none;
	background: var(--g-ink3);
	opacity: 0.5;
}
.oc-line--dash {
	width: 0;
	background: none;
	border-left: 2px dashed var(--g-ink3);
}
.oc-node {
	position: relative;
	display: flex;
	align-items: center;
	gap: 12px;
	width: 100%;
	max-width: 320px;
	min-height: 56px;
	padding: 10px 14px;
	border: 0;
	border-radius: 18px;
	background: var(--g-sheet-cell);
	color: var(--g-ink);
	text-align: left;
	box-shadow: inset 0 0 0 1.5px var(--oc-box-line);
}
button.oc-node:active,
.oc-kid:active {
	background: var(--g-icon-bg);
}
.oc-node--pill {
	width: auto;
	min-height: 44px;
	padding: 6px 14px 6px 8px;
	border-radius: 22px;
	gap: 8px;
}
.oc-more {
	margin-top: 12px;
	padding-left: 16px;
}
.oc-pill__label {
	font-size: 0.8125rem;
	line-height: 1.125rem;
	color: var(--g-ink2);
}
.oc-node--ghost {
	width: auto;
	min-height: 44px;
	justify-content: center;
	padding: 0 18px;
	border-radius: 22px;
	background: none;
	box-shadow: none;
	border: 2px dashed var(--g-ink3);
	color: var(--g-ink2);
	font-size: 0.8125rem;
}
.oc-node__body {
	flex: 1;
	min-width: 0;
	display: flex;
	flex-direction: column;
	gap: 1px;
}
.oc-node__eyebrow {
	font-size: 0.6875rem;
	line-height: 0.8125rem;
	font-weight: 600;
	letter-spacing: 0.06em;
	text-transform: uppercase;
	color: var(--g-ink2);
}
.oc-node__name {
	font-size: 0.9375rem;
	line-height: 1.25rem;
	font-weight: 600;
	white-space: nowrap;
	overflow: hidden;
	text-overflow: ellipsis;
}
.oc-node__sub {
	font-size: 0.8125rem;
	line-height: 1.125rem;
	color: var(--g-ink2);
	white-space: nowrap;
	overflow: hidden;
	text-overflow: ellipsis;
}
.oc-stack {
	display: inline-flex;
	gap: 2px;
	flex: none;
}

/* the person in focus: centred, avatar on top so a long name gets the full width */
.oc-node--focus {
	max-width: 360px;
	flex-direction: column;
	gap: 4px;
	padding: 20px 16px 18px;
	text-align: center;
	box-shadow: inset 0 0 0 3px var(--oc-box-line);
	animation: oc-enter var(--g-motion-state-change-duration) var(--g-motion-state-change-easing);
}
.oc-node--focus > .g-avatar {
	margin-bottom: 8px;
}
.oc-focus__name {
	margin: 0;
	font-size: 1.375rem;
	line-height: 1.75rem;
	font-weight: 600;
	letter-spacing: -0.26px;
	text-wrap: balance;
	overflow-wrap: anywhere;
}
.oc-focus__designation {
	margin: 0;
	font-size: 0.9375rem;
	line-height: 1.25rem;
	text-wrap: balance;
}
.oc-focus__meta {
	margin: 0;
	font-size: 0.8125rem;
	line-height: 1.125rem;
	color: var(--g-ink2);
}
.oc-focus__chips {
	display: flex;
	flex-wrap: wrap;
	justify-content: center;
	gap: 6px;
	margin-top: 10px;
}
@keyframes oc-enter {
	from {
		opacity: 0;
		transform: translateY(8px);
	}
	to {
		opacity: 1;
		transform: none;
	}
}

/* the team: two columns hung off one line down the middle gutter */
.oc-kids {
	width: 100%;
	max-width: 560px;
	display: grid;
	grid-template-columns: minmax(0, 1fr) minmax(0, 1fr);
	column-gap: 24px;
	row-gap: 12px;
	padding-top: 12px;
}
.oc-kid {
	position: relative;
	min-width: 0;
	display: flex;
	flex-direction: column;
	align-items: center;
	gap: 2px;
	padding: 14px 8px 12px;
	border: 0;
	border-radius: 18px;
	background: var(--g-sheet-cell);
	color: var(--g-ink);
	text-align: center;
	box-shadow: inset 0 0 0 1.5px var(--oc-box-line);
}
.oc-kid > .g-avatar {
	margin-bottom: 6px;
}
/* a short arm from each box to the line in the gutter */
.oc-kid::before {
	content: "";
	position: absolute;
	top: 50%;
	width: 12px;
	height: 2px;
	background: var(--g-ink3);
	opacity: 0.5;
}
.oc-kid:nth-child(odd)::before {
	right: -12px;
}
.oc-kid:nth-child(even)::before {
	left: -12px;
}
/* the line itself, drawn by the left column down to the last row's arm */
.oc-kid:nth-child(odd)::after {
	content: "";
	position: absolute;
	right: -13px;
	top: -12px;
	bottom: 0;
	width: 2px;
	background: var(--g-ink3);
	opacity: 0.5;
}
.oc-kid:nth-child(odd):nth-last-child(-n + 2)::after {
	bottom: 50%;
}
.oc-kid__name {
	max-width: 100%;
	font-size: 0.8125rem;
	line-height: 1.125rem;
	font-weight: 600;
	display: -webkit-box;
	-webkit-line-clamp: 2;
	-webkit-box-orient: vertical;
	overflow: hidden;
	overflow-wrap: anywhere;
}
.oc-kid__sub {
	max-width: 100%;
	font-size: 0.6875rem;
	line-height: 0.8125rem;
	color: var(--g-ink2);
	white-space: nowrap;
	overflow: hidden;
	text-overflow: ellipsis;
}
.oc-count {
	position: absolute;
	top: 8px;
	right: 10px;
	display: inline-flex;
	align-items: center;
	gap: 3px;
	font-size: 0.6875rem;
	color: var(--g-ink2);
	font-variant-numeric: tabular-nums;
}
.oc-away {
	font-size: 0.6875rem;
	line-height: 0.8125rem;
	font-weight: 600;
	color: var(--g-leave-ink);
}
.oc-node__sub .oc-away {
	font-size: inherit;
}
.oc-team-away {
	margin: 12px 0 0;
}

.oc-chip {
	display: inline-flex;
	align-items: center;
	gap: 6px;
	min-height: 28px;
	padding: 0 10px;
	border-radius: 14px;
	font-size: 0.75rem;
	line-height: 1rem;
	font-weight: 600;
	white-space: nowrap;
	background: var(--g-icon-bg);
	color: var(--g-ink2);
}
.oc-chip--away {
	background: rgb(var(--g-leave-rgb) / 0.14);
	color: var(--g-leave-ink);
}
.oc-chip--away::before {
	content: "";
	width: 6px;
	height: 6px;
	border-radius: 50%;
	background: var(--g-leave);
}
.oc-chip--sm {
	min-height: 22px;
	padding: 0 8px;
	font-size: 0.6875rem;
}
.oc-chip--sm.oc-chip--away::before {
	width: 5px;
	height: 5px;
}

.oc-sk-box {
	max-width: 320px;
}
.oc-sk-focus {
	max-width: 360px;
}

.oc-gap-h {
	padding: 12px 16px 4px;
	font-size: 0.75rem;
	font-weight: 600;
	line-height: 1.125rem;
	color: var(--g-ink2);
}
.oc-link {
	display: inline-flex;
	align-items: center;
	gap: 4px;
	min-height: 44px;
	padding: 0 10px;
	margin-right: -10px;
	border-radius: 22px;
	color: var(--g-accent-ink);
	font-size: 0.8125rem;
	line-height: 1.125rem;
	font-weight: 600;
	text-decoration: none;
	flex: none;
}
.oc-link:active {
	background: var(--g-icon-bg);
}

@media (prefers-reduced-motion: reduce) {
	.oc-chev {
		transition: none;
	}
	.oc-node--focus {
		animation: none;
	}
}
</style>
