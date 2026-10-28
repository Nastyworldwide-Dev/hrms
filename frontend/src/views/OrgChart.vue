<template>
	<GPage>
		<ShellHeader :title="__('Org chart')">
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
					:aria-label="__('Loading the org chart')"
				>
					<div v-for="i in 4" :key="i" class="oc-sk-row">
						<GSkeleton width="36px" height="36px" radius="50%" class="oc-sk-dot" />
						<span class="oc-sk-lines">
							<GSkeleton width="60%" height="14px" />
							<GSkeleton width="38%" height="10px" />
						</span>
					</div>
				</div>

				<!-- Error state, also when the request never produced a person -->
				<div v-else-if="nodeData.error || !person" class="g-empty">
					<AlertTriangle class="w-12 h-12 oc-warn-icon" />
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
									<GAvatar :image="p.image" :label="p.name" round />
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
								{{ __('Nobody called "%s" in this view.', [searchQuery.trim()]) }}
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
										<AlertTriangle class="w-4 h-4" />
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
												:aria-label="__('Fix %s in Desk', [item.name])"
											>
												{{ __("Fix in Desk") }}
											</a>
										</div>
									</template>
								</div>
							</div>
						</section>

						<!-- Reports to section -->
						<section v-if="chainRows.length" class="oc-sec">
							<h2 class="oc-sec__title">{{ __("Reports to") }}</h2>
							<div class="g-form-group">
								<button
									v-for="p in chainRows"
									:key="p.id || p.name"
									class="g-row g-row--tappable"
									@click="focusPerson(p.id)"
									:disabled="!!p.message"
								>
									<GAvatar v-if="!p.message" :image="p.image" :label="p.name" round />
									<span v-else class="g-row__well oc-well-warn">
										<UserRoundX class="w-4 h-4" />
									</span>
									<span class="g-row__body">
										<span class="g-row__label">{{
											p.message ? __("Manager has left") : p.name
										}}</span>
										<span v-if="p.message" class="g-row__sub oc-wrap">
											{{ __("HR sets a new manager in Desk") }}
										</span>
									</span>
								</button>
							</div>
						</section>

						<!-- Focus card -->
						<section ref="focusCard" class="oc-focus-card" tabindex="-1" :aria-label="person.name">
							<div class="oc-focus-card__top">
								<GAvatar :size="64" round :image="person.image" :label="person.name" />
								<div class="oc-focus-card__text">
									<h2 class="oc-focus-card__name">{{ person.name }}</h2>
									<p class="oc-focus-card__designation">{{ person.designation }}</p>
									<p class="oc-focus-card__meta">{{ subline(person) }}</p>
									<p v-if="isHR" class="oc-focus-card__meta">{{ person.company }}</p>
								</div>
							</div>
							<div class="oc-focus-card__chips">
								<span v-if="person.id === userId" class="oc-chip">{{ __("This is you") }}</span>
								<span v-if="person.away" class="oc-chip oc-chip--away">{{
									__("Away today")
								}}</span>
								<span class="oc-chip">
									{{ person.team_size ? __("Team of %s", [person.team_size]) : __("No team") }}
								</span>
							</div>
						</section>

						<!-- No manager and no reports -->
						<div v-if="isEmpty" class="g-empty">
							<Network class="w-12 h-12 text-ink-3" />
							<h2 class="g-empty__title">{{ __("No manager set yet") }}</h2>
							<p class="g-empty__body">{{ __("HR sets this in Desk.") }}</p>
						</div>

						<!-- Team section, always shown -->
						<section class="oc-sec">
							<div class="oc-sec__head">
								<h2 class="oc-sec__title">{{ __("Team") }} · {{ teamDisplay.all.length }}</h2>
								<span v-if="teamAwayCount > 0" class="oc-sec__aside">
									{{ __("%s away today", [teamAwayCount]) }}
								</span>
							</div>
							<div id="oc-team-list" class="g-form-group">
								<div v-if="!teamDisplay.all.length" class="g-row">
									<span class="g-row__sub oc-wrap">
										{{ __("No one reports to %s.", [person.name]) }}
									</span>
								</div>
								<button
									v-for="p in teamDisplay.shown"
									:key="p.id"
									class="g-row g-row--tappable"
									@click="focusPerson(p.id)"
								>
									<GAvatar :image="p.image" :label="p.name" round />
									<span class="g-row__body">
										<span class="g-row__label">{{ p.name }}</span>
										<span class="g-row__sub">{{ subline(p) }}</span>
									</span>
									<span v-if="p.away" class="oc-chip oc-chip--sm oc-chip--away">
										{{ __("Away today") }}
									</span>
								</button>
								<button
									v-if="teamDisplay.more > 0 || teamExpanded"
									class="g-row g-row--tappable"
									:aria-expanded="teamExpanded"
									aria-controls="oc-team-list"
									@click="teamExpanded = !teamExpanded"
								>
									<span class="g-row__body">
										<span class="g-row__label oc-strong">
											{{
												teamExpanded
													? __("Show fewer")
													: __("See all %s", [teamDisplay.all.length])
											}}
										</span>
									</span>
									<ChevronDown class="g-row__chevron oc-chev" />
								</button>
							</div>
						</section>

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
										<GAvatar :image="p.image" :label="p.name" round />
										<span class="g-row__body">
											<span class="g-row__label">{{ p.name }}</span>
											<span class="g-row__sub">{{ subline(p) }}</span>
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
	AlertTriangle,
	ChevronDown,
	LocateFixed,
	Network,
	Search,
	UserRoundX,
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
const gapsExpanded = ref(false)
const focusCard = ref(null)

// HR is told by the server: only HR receives data.gaps
const isHR = computed(() => nodeData.data?.gaps !== undefined)

// Load the org chart node data (params are not reactive in frappe-ui: refetch on focus change)
const nodeData = createResource({
	url: "hrms.api.org_chart.get_node",
})
watch(focusedId, (id) => nodeData.submit(id ? { employee: id } : {}), { immediate: true })

// Compute current person
const person = computed(() => nodeData.data?.person)
const reports = computed(() => nodeData.data?.reports || [])

// Check if empty (no manager and no reports)
const isEmpty = computed(() => {
	return !chainRows.value.length && !reports.value.length
})

// Build chain up (reports to)
const chainRows = computed(() => {
	if (!nodeData.data || !nodeData.data.chain_up) return []
	const chain = nodeData.data.chain_up || []
	return makeChainRows(chain).map((entry) => ({
		...entry,
		name: entry.name || __("(no name)"),
	}))
})

// Team display with preview logic
const teamDisplay = computed(() => {
	const all = reports.value
	const preview = teamPreview(all, teamExpanded.value ? all.length : 5)
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
		{ key: "left", title: __("Manager left"), rows: g.left_manager || [] },
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

.oc-focus-card {
	display: flex;
	flex-direction: column;
	gap: 14px;
	padding: 20px 16px;
	border-radius: 26px;
	background: var(--g-sheet-cell);
	box-shadow: inset 0 1px 0 var(--g-rim-hi), inset 0 -1px 0 var(--g-rim-lo);
	margin-bottom: 24px;
	animation: oc-enter var(--g-motion-state-change-duration) var(--g-motion-state-change-easing);
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
.oc-focus-card__top {
	display: flex;
	gap: 14px;
	align-items: center;
}
.oc-focus-card__text {
	min-width: 0;
	flex: 1;
}
.oc-focus-card__name {
	margin: 0;
	font-size: 1.375rem;
	line-height: 1.75rem;
	letter-spacing: -0.4px;
	overflow-wrap: anywhere;
	font-weight: 700;
}
.oc-focus-card__designation {
	margin: 2px 0 0;
	font-size: 1.0625rem;
	line-height: 1.375rem;
	overflow-wrap: anywhere;
}
.oc-focus-card__meta {
	margin: 2px 0 0;
	font-size: 0.9375rem;
	line-height: 1.25rem;
	color: var(--g-ink2);
	overflow-wrap: anywhere;
}
.oc-focus-card__chips {
	display: flex;
	flex-wrap: wrap;
	gap: 8px;
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

.oc-sk-row {
	display: flex;
	align-items: center;
	gap: 12px;
	padding: 12px 16px;
	min-height: 54px;
}
.oc-sk-dot {
	flex: none;
}
.oc-sk-lines {
	flex: 1;
	display: flex;
	flex-direction: column;
	gap: 6px;
}

.oc-gap-h {
	padding: 12px 16px 4px;
	font-size: 0.8125rem;
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
	.oc-focus-card {
		animation: none;
	}
}
</style>
