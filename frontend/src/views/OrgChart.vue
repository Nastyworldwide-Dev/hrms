<template>
	<GPage>
		<ShellHeader :title="__('Org chart')">
			<template #actions>
				<button
					v-if="!isSearching"
					class="g-icon-btn--you"
					:aria-disabled="isOnSelf"
					@click="goToSelf"
				>
					<LocateFixed class="h-4 w-4" />
					<span>{{ __("You") }}</span>
				</button>
			</template>
		</ShellHeader>
		<ion-content class="ion-padding g-page__content">
			<div class="w-full max-w-content-column-lg mx-auto px-4">
				<!-- Search bar and company picker -->
				<div class="flex flex-col gap-3 mb-6">
					<GSearchBar
						v-model="searchQuery"
						:placeholder="__('Search by name')"
						:label="__('Search by name')"
					/>
				</div>

				<!-- Loading state -->
				<div v-if="nodeData.loading" class="g-skeleton" aria-busy="true">
					<div v-for="i in 4" :key="i" class="sk-row">
						<span class="sk c"></span>
						<span class="l">
							<span class="sk" style="height: 14px; width: 60%"></span>
							<span class="sk" style="height: 10px; width: 38%"></span>
						</span>
					</div>
				</div>

				<!-- Error state -->
				<div v-else-if="nodeData.error" class="g-empty">
					<AlertTriangle class="w-12 h-12 text-ink-3" />
					<h2 class="g-empty__title">{{ __("Could not load the chart") }}</h2>
					<p class="g-empty__body">{{ __("Check your connection, then try again.") }}</p>
					<GButton :label="__('Retry')" :disabled="retrying" @click="retryFetch" />
				</div>

				<!-- Empty state (no manager, no reports) -->
				<div v-else-if="!nodeData.data" class="g-skeleton" aria-busy="true"></div>

				<!-- Loaded content -->
				<template v-else-if="nodeData.data && person">
					<!-- Search results -->
					<template v-if="isSearching">
						<section v-if="searchResults.length" class="sec">
							<h2 class="sec__title">
								{{ searchResults.length }}
								{{ searchResults.length === 1 ? __("match") : __("matches") }}
							</h2>
							<div class="g-form-group">
								<button
									v-for="p in searchResults.slice(0, 8)"
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
						<div v-else class="g-empty">
							<Search class="w-12 h-12 text-ink-3" />
							<h2 class="g-empty__title">{{ __("No one found") }}</h2>
							<p class="g-empty__body">
								{{
									__('Nobody called "%s" in %s.', [
										searchQuery.trim(),
										isHR.value ? __("any company") : __("your company"),
									])
								}}
							</p>
						</div>
					</template>

					<!-- Normal view -->
					<template v-else>
						<!-- HR gaps section -->
						<section v-if="isHR && gaps.total > 0" class="sec gap-section">
							<button
								class="g-row g-row--tappable"
								:aria-expanded="gapsExpanded"
								@click="gapsExpanded = !gapsExpanded"
							>
								<AlertTriangle class="w-6 h-6 text-ink-3" style="color: var(--g-warn-ink)" />
								<span class="g-row__body">
									<span class="g-row__label">{{ gapsMessage }}</span>
								</span>
								<ChevronDown class="g-row__chevron" />
							</button>
							<div v-if="gapsExpanded" class="gap-detail">
								<div v-for="item in gaps.all" :key="item.id || item.name" class="gap-row">
									<span>{{ item.name }}</span>
									<a :href="desktopLink(item.id)" target="_self" class="link">
										{{ __("Fix in Desk") }}
									</a>
								</div>
							</div>
						</section>

						<!-- Reports to section -->
						<section v-if="chainRows.length" class="sec">
							<h2 class="sec__title">{{ __("Reports to") }}</h2>
							<div class="g-form-group">
								<button
									v-for="p in chainRows"
									:key="p.id || p.name"
									class="g-row g-row--tappable"
									@click="focusPerson(p.id)"
									:disabled="!!p.message"
								>
									<GAvatar v-if="!p.message" :image="p.image" :label="p.name" round />
									<span v-else class="g-row__well g-row__well--warn">
										<UserRoundX class="w-4 h-4" />
									</span>
									<span class="g-row__body">
										<span class="g-row__label">{{
											p.message ? __("Manager has left") : p.name
										}}</span>
										<span v-if="p.message" class="g-row__sub wrap">
											{{ __("HR sets a new manager in Desk") }}
										</span>
									</span>
								</button>
							</div>
						</section>

						<!-- Focus card -->
						<section class="focus-card">
							<div class="focus-card__top">
								<GAvatar :size="72" round :image="person.image" :label="person.name" />
								<div class="focus-card__text">
									<h1 class="focus-card__name">{{ person.name }}</h1>
									<p class="focus-card__designation">{{ person.designation }}</p>
									<p class="focus-card__meta">{{ subline(person) }}</p>
									<p v-if="isHR" class="focus-card__company">{{ person.company }}</p>
								</div>
							</div>
							<div class="focus-card__chips">
								<span v-if="person.id === userId" class="chip">{{ __("This is you") }}</span>
								<span v-if="person.away" class="chip chip--away">{{ __("Away today") }}</span>
								<span class="chip">
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

						<!-- Team section -->
						<section v-if="teamDisplay.all.length > 0" class="sec">
							<div class="sec__head">
								<h2 class="sec__title">{{ __("Team") }} · {{ teamDisplay.all.length }}</h2>
								<span v-if="teamAwayCount > 0" class="sec__aside">
									{{ __("%s away today", [teamAwayCount]) }}
								</span>
							</div>
							<div class="g-form-group">
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
									<span v-if="p.away" class="chip chip--sm chip--away">
										{{ __("Away today") }}
									</span>
								</button>
								<button
									v-if="teamDisplay.more > 0"
									class="g-row g-row--tappable"
									:aria-expanded="teamExpanded"
									@click="teamExpanded = !teamExpanded"
								>
									<span class="g-row__body">
										<span class="g-row__label">
											{{
												teamExpanded
													? __("Show fewer")
													: __("See all %s", [teamDisplay.all.length])
											}}
										</span>
									</span>
									<ChevronDown class="g-row__chevron" />
								</button>
							</div>
						</section>

						<!-- Same manager section (peers) -->
						<section v-if="peers.length > 0" class="sec">
							<button
								class="g-row g-row--tappable"
								:aria-expanded="peersExpanded"
								@click="peersExpanded = !peersExpanded"
							>
								<span class="g-row__body">
									<span class="g-row__label"> {{ __("Same manager") }} · {{ peers.length }} </span>
								</span>
								<ChevronDown class="g-row__chevron" />
							</button>
							<div v-if="peersExpanded" class="g-form-group">
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
import { computed, inject, ref, watch } from "vue"
import { useRouter, useRoute } from "vue-router"
import { IonContent } from "@ionic/vue"

import GPage from "@/components/glass/GPage.vue"
import GAvatar from "@/components/glass/GAvatar.vue"
import GButton from "@/components/glass/GButton.vue"
import GSearchBar from "@/components/glass/GSearchBar.vue"
import ShellHeader from "@/components/ShellHeader.vue"

import { createResource } from "frappe-ui"
import {
	subline,
	teamPreview,
	awayCount as countAway,
	chainRows as makeChainRows,
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
const retrying = ref(false)

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
		name: entry.name || "(no name)",
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

const gapsMessage = computed(() => {
	const parts = []
	if (gaps.value.noManager > 0) {
		parts.push(
			gaps.value.noManager === 1
				? __("%s person has no manager set", [gaps.value.noManager])
				: __("%s people have no manager set", [gaps.value.noManager])
		)
	}
	if (gaps.value.leftManager > 0) {
		parts.push(__("%s report to someone who has left", [gaps.value.leftManager]))
	}
	return parts.join(" · ")
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

function retryFetch() {
	retrying.value = true
	nodeData.submit(focusedId.value ? { employee: focusedId.value } : {})
	setTimeout(() => {
		retrying.value = false
	}, 1500)
}

function desktopLink(id) {
	return `/desk/employee/${id}`
}
</script>

<style scoped>
.g-icon-btn--you {
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
.g-icon-btn--you[aria-disabled="true"] {
	opacity: 0.4;
}

.g-form-row {
	display: flex;
	align-items: center;
	gap: 12px;
	min-height: 44px;
	padding: 0 16px;
}

.g-form-row__label {
	flex: none;
	font-size: 1.0625rem;
	line-height: 1.375rem;
}

.g-select {
	position: relative;
	display: flex;
	flex: 1;
	min-width: 0;
}

.g-select__native {
	appearance: none;
	-webkit-appearance: none;
	width: 100%;
	min-height: 44px;
	padding: 8px 24px 8px 0;
	border: 0;
	background: transparent;
	text-align: right;
	text-align-last: right;
	text-overflow: ellipsis;
	font-size: 1.0625rem;
	cursor: pointer;
}

.g-select__chevron {
	position: absolute;
	top: 50%;
	right: 0;
	width: 16px;
	height: 16px;
	transform: translateY(-50%);
	color: var(--g-ink3);
	pointer-events: none;
}

.sec {
	display: flex;
	flex-direction: column;
	gap: 8px;
	margin-bottom: 24px;
}

.sec__head {
	display: flex;
	align-items: baseline;
	justify-content: space-between;
	gap: 8px;
	padding: 0 16px;
}

.sec__title {
	margin: 0;
	font-size: 0.8125rem;
	line-height: 1.125rem;
	color: var(--g-ink2);
	font-weight: 400;
}

.sec__aside {
	font-size: 0.8125rem;
	line-height: 1.125rem;
	color: var(--g-leave-ink);
	font-weight: 600;
}

.g-search {
	position: relative;
	display: block;
	width: 100%;
	color: var(--g-ink3);
}

.g-search__input {
	width: 100%;
	min-height: 44px;
	padding: 12px 48px 12px 34px;
	border: 1px solid var(--g-glass-rim);
	border-radius: 12px;
	background: var(--g-icon-bg);
	color: var(--g-ink);
	font-size: 0.9375rem;
	line-height: 1.25rem;
}

.g-search__input::placeholder {
	color: var(--g-ink-muted);
	opacity: 1;
}

.g-search__icon {
	position: absolute;
	top: 50%;
	left: 10px;
	transform: translateY(-50%);
	pointer-events: none;
}

.g-search__clear {
	position: absolute;
	top: 50%;
	right: 0;
	transform: translateY(-50%);
	width: 44px;
	height: 44px;
	border: 0;
	background: transparent;
	color: var(--g-ink3);
	display: grid;
	place-items: center;
	cursor: pointer;
	border-radius: 22px;
}

.g-form-group {
	display: flex;
	flex-direction: column;
	border-radius: 26px;
	background: var(--g-sheet-cell);
	overflow: hidden;
}

.g-row {
	position: relative;
	display: flex;
	align-items: center;
	gap: 12px;
	width: 100%;
	min-height: 54px;
	padding: 12px 16px;
	background: transparent;
	border: 0;
	text-align: left;
	color: var(--g-ink);
	transition: background 90ms ease-out;
}

.g-row + .g-row::before {
	content: "";
	position: absolute;
	top: 0;
	left: 16px;
	right: 16px;
	height: 1px;
	background: var(--g-hair);
}

.g-row--tappable {
	cursor: pointer;
}

.g-row--tappable:active {
	background: var(--g-icon-bg);
}

.g-row__body {
	display: flex;
	flex-direction: column;
	flex: 1;
	min-width: 0;
}

.g-row__label {
	font-size: 1.0625rem;
	line-height: 1.375rem;
	letter-spacing: -0.4px;
	overflow: hidden;
	text-overflow: ellipsis;
	white-space: nowrap;
}

.g-row__sub {
	font-size: 0.75rem;
	line-height: 1.3333;
	color: var(--g-ink2);
	overflow: hidden;
	text-overflow: ellipsis;
	white-space: nowrap;
}

.g-row__sub.wrap {
	white-space: normal;
	overflow-wrap: anywhere;
}

.g-row__chevron {
	flex: none;
	width: 7px;
	height: 12px;
	color: var(--g-ink3);
	transition: transform 280ms cubic-bezier(0.32, 0.72, 0, 1);
}

.g-row[aria-expanded="true"] .g-row__chevron {
	transform: rotate(180deg);
}

.g-row__well {
	flex: none;
	display: flex;
	align-items: center;
	justify-content: center;
	width: 29px;
	height: 29px;
	border-radius: 8px;
	background: var(--g-icon-bg);
	color: var(--g-ink2);
}

.g-row__well--warn {
	background: var(--g-warn-bg);
	color: var(--g-warn-ink);
}

.focus-card {
	display: flex;
	flex-direction: column;
	gap: 14px;
	padding: 20px 16px;
	border-radius: 26px;
	background: var(--g-sheet-cell);
	box-shadow: inset 0 1px 0 var(--g-rim-hi), inset 0 -1px 0 var(--g-rim-lo);
	margin-bottom: 24px;
	animation: enter 340ms cubic-bezier(0.32, 0.72, 0, 1);
}

@keyframes enter {
	from {
		opacity: 0;
		transform: translateY(8px);
	}
	to {
		opacity: 1;
		transform: none;
	}
}

.focus-card__top {
	display: flex;
	gap: 14px;
	align-items: center;
}

.focus-card__text {
	min-width: 0;
	flex: 1;
}

.focus-card__name {
	margin: 0;
	font-size: 1.375rem;
	line-height: 1.75rem;
	letter-spacing: -0.4px;
	overflow-wrap: anywhere;
	font-weight: 700;
}

.focus-card__designation {
	margin-top: 2px;
	margin-bottom: 0;
	font-size: 1.0625rem;
	line-height: 1.375rem;
	overflow-wrap: anywhere;
}

.focus-card__meta {
	margin-top: 2px;
	margin-bottom: 0;
	font-size: 0.9375rem;
	line-height: 1.25rem;
	color: var(--g-ink2);
	overflow-wrap: anywhere;
}

.focus-card__company {
	margin-top: 2px;
	margin-bottom: 0;
	font-size: 0.9375rem;
	line-height: 1.25rem;
	color: var(--g-ink2);
	overflow-wrap: anywhere;
}

.focus-card__chips {
	display: flex;
	flex-wrap: wrap;
	gap: 8px;
}

.chip {
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

.chip--away {
	background: var(--g-leave-bg);
	color: var(--g-leave-ink);
}

.chip--away::before {
	content: "";
	width: 6px;
	height: 6px;
	border-radius: 50%;
	background: var(--g-leave-dot);
}

.chip--sm {
	min-height: 22px;
	padding: 0 8px;
	font-size: 0.6875rem;
}

.chip--sm.chip--away::before {
	width: 5px;
	height: 5px;
}

.g-empty {
	display: flex;
	flex-direction: column;
	align-items: center;
	padding: 56px 24px;
	text-align: center;
}

.g-empty__title {
	margin-top: 12px;
	margin-bottom: 0;
	font-size: 1.375rem;
	line-height: 1.75rem;
	font-weight: 700;
}

.g-empty__body {
	margin-top: 4px;
	max-width: 320px;
	font-size: 0.9375rem;
	line-height: 1.25rem;
	color: var(--g-ink2);
}

.g-empty .g-btn {
	margin-top: 20px;
}

.sk-row {
	display: flex;
	align-items: center;
	gap: 12px;
	padding: 12px 16px;
	min-height: 54px;
}

.sk {
	border-radius: 10px;
	background: var(--g-track-solid);
	animation: pulse 1.2s ease-in-out infinite alternate;
}

@keyframes pulse {
	from {
		opacity: 0.45;
	}
	to {
		opacity: 1;
	}
}

.sk.c {
	width: 36px;
	height: 36px;
	border-radius: 50%;
	flex: none;
}

.l {
	flex: 1;
	display: flex;
	flex-direction: column;
	gap: 6px;
}

.link {
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

.link:active {
	background: var(--g-icon-bg);
}

.gap-section {
	margin-bottom: 24px;
}

.gap-detail {
	padding: 12px 16px;
	border-top: 1px solid var(--g-hair);
}

.gap-row {
	display: flex;
	align-items: center;
	justify-content: space-between;
	padding: 8px 0;
	font-size: 0.9375rem;
}
</style>
