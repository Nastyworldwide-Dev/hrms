<template>
	<BaseLayout :pageTitle="__('KPI')">
		<template #body>
			<div class="flex flex-col w-full max-w-3xl mx-auto px-4 py-7 gap-8 lg:px-7 lg:py-9">
				<!-- Whose KPI. GSegmented refuses to draw a one-option control, so
				     for everyone but the CEO this line renders nothing at all and the
				     page is exactly what it was. -->
				<GSegmented
					v-if="canViewTeamKpi.data"
					:buttons="TAB_BUTTONS"
					v-model="activeTab"
					:label="__('Whose KPI')"
				/>

				<template v-if="activeTab === MINE">
					<ResourceError :resource="dashboard" what="your KPI dashboard" />
					<!-- Filters -->
					<div
						v-if="years.length"
						class="flex flex-wrap items-end gap-x-6 gap-y-3 border-b-2 border-divider pb-5"
					>
						<div class="flex min-w-0 flex-col gap-1.5">
							<label class="g-eyebrow" for="kpi-year-filter">{{ __("Year") }}</label>
							<select
								id="kpi-year-filter"
								v-model="selectedYear"
								@change="onYearChange"
								class="kpi-filter g-focusable"
							>
								<option v-for="y in years" :key="y" :value="y">{{ y }}</option>
							</select>
						</div>
						<div class="flex min-w-0 flex-col gap-1.5">
							<label class="g-eyebrow" for="kpi-cycle-filter">
								{{ __("Appraisal cycle") }}
							</label>
							<select
								id="kpi-cycle-filter"
								v-model="selectedCycle"
								@change="refetch"
								class="kpi-filter g-focusable"
							>
								<option :value="ALL_CYCLES">{{ __("All Appraisal Cycles") }}</option>
								<option v-for="c in cycles" :key="c" :value="c">{{ c }}</option>
							</select>
						</div>
					</div>

					<!-- The SAME component the drill-down renders. One layout for
					     "my KPI" and "their KPI", because two would drift and the
					     drift would be invisible: both render, and only one would be
					     right about somebody's performance review. -->
					<KpiDetail v-if="dashboard.data && current" :data="dashboard.data" />

					<GEmptyState
						v-else-if="dashboard.data"
						:title="__('No appraisals yet')"
						:body="__('Your KPI appears here once a review cycle opens for you')"
					/>

					<!-- loading: the missing fourth state — without it the page was a
				     blank shell during the initial fetch. -->
					<div v-else class="flex items-center justify-center gap-3 py-12 text-ink-600">
						<LoadingIndicator class="h-5 w-5 text-accent-ink" />
						<span class="text-caption">{{ __("Loading your KPIs…") }}</span>
					</div>
				</template>

				<!-- ONE PERSON'S DETAIL — the same layout as My KPI, pointed at
				     somebody else. It REPLACES the list rather than stacking under
				     it: a page carrying two heroes and two score rings has no
				     answer to "whose number is this". -->
				<template v-else-if="openedName">
					<button
						type="button"
						class="g-seclink g-focusable self-start underline underline-offset-link text-ink-800"
						@click="closeEmployee({ restoreFocus: true })"
					>
						← {{ __("Back to {0}", [teamTabLabel]) }}
					</button>
					<ResourceError :resource="employeeKpi" what="this employee's KPI" />
					<!-- Gated on WHO THE PAYLOAD IS ABOUT, never on whether one
					     exists. frappe-ui does not clear `.data` when a new submit
					     starts, and employeeKpi is a module singleton — so on
					     "open A, back, open B" the truthiness test was still true
					     and still holding A's payload. B's name rendered above A's
					     score, A's grade, A's ring, A's KRA targets and A's
					     feedback: somebody else's performance review under the
					     wrong name, solid, with no spinner, because the loading
					     branch below became unreachable after the first open. -->
					<KpiDetail
						v-if="openedDetail && !employeeKpi.error"
						ref="detailRef"
						:data="openedDetail"
						:heading="openedName"
					/>
					<div
						v-else-if="employeeKpi.loading"
						class="flex items-center justify-center gap-3 py-12 text-ink-600"
					>
						<LoadingIndicator class="h-5 w-5 text-accent-ink" />
						<span class="text-caption">{{ __("Loading…") }}</span>
					</div>
				</template>

				<!-- TEAM KPI — the list. Read-only, and the v-if is a convenience,
				     not the fence: hrms.api.kpi.get_team_kpi re-checks the caller's
				     tier and refuses everyone else. -->
				<template v-else>
					<ResourceError :resource="teamResource" what="the team KPI view" />

					<!-- same filter bar geometry as My KPI, one control wider -->
					<div
						v-if="teamYears.length"
						class="flex flex-wrap items-end gap-x-6 gap-y-3 border-b-2 border-divider pb-5"
					>
						<div class="flex min-w-0 flex-col gap-1.5">
							<label class="g-eyebrow" for="team-year-filter">{{ __("Year") }}</label>
							<select
								id="team-year-filter"
								v-model="teamYear"
								@change="onTeamYearChange"
								class="kpi-filter g-focusable"
							>
								<option v-for="y in teamYears" :key="y" :value="y">{{ y }}</option>
							</select>
						</div>
						<div class="flex min-w-0 flex-col gap-1.5">
							<label class="g-eyebrow" for="team-cycle-filter">
								{{ __("Appraisal cycle") }}
							</label>
							<select
								id="team-cycle-filter"
								v-model="teamCycle"
								@change="fetchTeam"
								class="kpi-filter g-focusable"
							>
								<option :value="ALL_CYCLES">{{ __("All Appraisal Cycles") }}</option>
								<option v-for="c in teamCycles" :key="c" :value="c">{{ c }}</option>
							</select>
						</div>
						<!-- Only drawn when there IS more than one company to choose
						     between: a one-option selector is not a control. Never for
						     a manager — their scope is the people who report to them,
						     not a slice of the org chart, so a company or department
						     filter over it is a control with nothing to control. -->
						<div
							v-if="!isManagerTier && teamCompanies.length > 1"
							class="flex min-w-0 flex-col gap-1.5"
						>
							<label class="g-eyebrow" for="team-company-filter">
								{{ __("Company") }}
							</label>
							<select
								id="team-company-filter"
								v-model="teamCompany"
								@change="onTeamCompanyChange"
								class="kpi-filter g-focusable"
							>
								<option value="">{{ __("All companies") }}</option>
								<option v-for="c in teamCompanies" :key="c" :value="c">{{ c }}</option>
							</select>
						</div>
						<!-- The Department SELECT belongs to the manager tier only. CEO and
						     HR walk the tree instead, and for them this carried exactly one
						     option that changed a value fetchTree never sends — a control
						     that cannot be changed and would do nothing if it could. -->
						<div v-if="isManagerTier" class="flex min-w-0 flex-col gap-1.5">
							<label class="g-eyebrow" for="team-department-filter">
								{{ __("Department") }}
							</label>
							<select
								id="team-department-filter"
								v-model="teamDepartment"
								@change="fetchTeam"
								class="kpi-filter g-focusable"
							>
								<option value="">{{ __("All departments") }}</option>
								<option v-for="d in teamDepartments" :key="d" :value="d">{{ d }}</option>
							</select>
						</div>
					</div>

					<!-- Hero: the average of whatever the filters currently select -->
					<!-- Stays mounted while refetching. Unmounting it collapsed ~140px
					     out of the page the instant a filter changed — moving the tap
					     target under the user's finger — and took the scope eyebrow with
					     it, which is the only line saying what they just chose. -->
					<!-- teamYears gates the filter bar too (there is nothing to filter on
					     an empty hub), and a line reading back a selection made with
					     controls that are not on screen is noise. Same rule as the
					     one-option selector above.
					     !error matters more than it looks: frappe-ui's handleError does
					     `out.data = out.previousData`, so after any successful load
					     `.data` SURVIVES a failed refetch — the hero kept rendering the
					     previous score, headcount, top and ring, solid, under an eyebrow
					     naming the new filter, right beside the error alert. The answer
					     goes when it is no longer an answer; the controls stay. -->
					<!-- Bound to the SHARED payload, like everything else on this tab.
					     Gating it on teamKpi made the whole answer block — score, badge,
					     ring — vanish for the CEO and HR, because fetchTeam early-returns
					     to fetchTree and never submits teamKpi. The screen read as
					     controls, then tables, and no number. -->
					<div v-if="teamData && teamYears.length && !teamResource.error">
						<!-- The scope line is NOT gated on headcount. A select truncates a
						     long company name ("Astra Holdings International (Labuan) Ltd
						     - A…"), so on an empty result it would otherwise be the only
						     record of what was chosen — and two companies sharing a prefix
						     would read identically. The one moment you most need to know
						     what you filtered to is the moment it returned nothing. -->
						<div class="g-eyebrow">{{ scopeLabel }}</div>
						<div
							v-if="teamSummary && teamSummary.headcount"
							class="flex items-center justify-between mt-3 border-t-2 border-divider pt-4"
						>
							<div class="flex flex-col gap-2">
								<GSkeleton
									v-if="teamResource.loading"
									width="150px"
									height="var(--g-type-clock-size)"
								/>
								<div v-else class="font-sans font-extrabold text-clock leading-none tabular-nums">
									{{ score1(teamSummary.average_score)
									}}<span class="text-button-label text-ink-500 font-normal"> / 100</span>
								</div>
								<!-- These go with the score: rendering last fetch's headcount
								     and top solid, under an eyebrow already naming the NEW
								     filter, states the previous answer as the current one. -->
								<GSkeleton v-if="teamResource.loading" width="180px" height="20px" />
								<div v-else class="flex items-center gap-2.5">
									<GBadge variant="accent">
										{{ __("{0} appraised", [teamSummary.headcount]) }}
									</GBadge>
									<span class="text-xs font-sans font-extrabold text-ink-700">
										{{ __("Top") }} {{ score1(teamSummary.top_score) }}
									</span>
								</div>
							</div>
							<!-- Integer in the ring, one decimal in the hero beside it: a
							     25px/800 numeral inside a 69px circle buys nothing from the
							     extra glyph, and the exact figure is already alongside it. -->
							<GProgressRing
								:score="Math.round(Number(teamSummary.average_score) || 0)"
								:max="100"
								:label="__('Average score')"
								:loading="teamResource.loading"
							/>
						</div>
					</div>

					<!-- WHERE YOU ARE. A breadcrumb, not a back button: this walk has
					     real depth (All Departments › Sales › Sales East) and the
					     user needs to jump back more than one level. -->
					<!-- Rendered at EVERY depth, including the root, for two reasons: it
					     is the only element that survives a drill, so it is the one thing
					     focus can land on afterwards; and a walk with no visible position
					     is a walk you cannot get out of. An ordered list because a
					     breadcrumb IS a sequence — without it a screen reader hears one
					     undifferentiated run with no item count and no "you are here". -->
					<nav
						v-if="!isManagerTier && treeCrumbs.length"
						class="text-caption text-ink-600"
						:aria-label="__('Department path')"
					>
						<ol class="flex flex-wrap items-center gap-x-2.5 gap-y-1">
							<li
								v-for="(crumb, i) in treeCrumbs"
								:key="crumb.name"
								class="flex items-center gap-x-2.5"
							>
								<button
									v-if="i < treeCrumbs.length - 1"
									type="button"
									class="g-seclink g-focusable underline text-ink-800"
									@click="openDepartment(crumb.name)"
								>
									{{ crumb.label }}
								</button>
								<span
									v-else
									ref="nodeEl"
									tabindex="-1"
									aria-current="page"
									class="font-sans font-semibold text-ink-800 kpi-node-heading"
								>
									{{ crumb.label }}
								</span>
								<ChevronRight
									v-if="i < treeCrumbs.length - 1"
									class="h-3 w-3 flex-none text-ink-500"
									aria-hidden="true"
								/>
							</li>
						</ol>
					</nav>

					<!-- The departments directly inside this node. Each row carries its
					     own roll-up — the average over every PERSON beneath it, which is
					     headcount-weighted by construction. -->
					<div v-if="!isManagerTier && treeDepartments.length">
						<h2 class="g-eyebrow mb-2.5">{{ __("Departments") }}</h2>
						<GDataTable
							:columns="DEPARTMENT_COLUMNS"
							:rows="treeDepartmentRows"
							:caption="__('Departments inside {0}', [treeNodeLabel])"
							:loading="teamResource.loading"
							@row-action="openDepartmentRow"
						/>
					</div>

					<!-- §6.3: a score someone may dispute is read on a SOLID surface,
					     never through a moving tint — GDataTable, not a glass panel.
					     Hidden on error: GDataTable shows its #empty slot whenever
					     rows is empty and loading is false, so a failed fetch put
					     "Nobody has an appraisal" directly under the error banner —
					     two contradictory answers to the same question. -->
					<!-- The live region is a SUMMARY and it is mounted unconditionally.
					     It used to be the Scores wrapper: every filter change queued the
					     whole table for announcement, and its own v-if unmounted the
					     region, so the one transition that most needs announcing —
					     error then recovered — was the one assistive tech skipped. -->
					<span class="g-sr" role="status" aria-live="polite">
						{{
							teamResource.error || teamResource.loading
								? ""
								: !teamYears.length
								? __("No appraisals yet")
								: teamSummary && teamSummary.headcount
								? __("{0}: {1} appraised, average {2}", [
										scopeLabel,
										teamSummary.headcount,
										score1(teamSummary.average_score),
								  ])
								: __("{0}: no appraisals", [scopeLabel])
						}}
					</span>

					<!-- Suppressed at the ROOT when empty: "People here" there means
					     everyone filed against the root department itself, which is
					     nobody, and an empty table directly under a hero counting the
					     whole company reads as a contradiction rather than a fact. -->
					<div v-if="!teamResource.error && !(atTreeRoot && !teamRows.length)">
						<h2 ref="scoresHeadingEl" tabindex="-1" class="g-eyebrow mb-2.5 kpi-scores-heading">
							{{ isManagerTier ? __("Scores") : __("People here") }}
						</h2>
						<GDataTable
							:columns="TEAM_COLUMNS"
							:rows="teamRows"
							:caption="
								isManagerTier ? __('Team KPI scores') : __('People in {0}', [treeNodeLabel])
							"
							:loading="teamResource.loading"
							@row-action="openEmployee"
						>
							<template #empty>
								<GEmptyState
									:title="__('No appraisals here')"
									:body="
										isManagerTier
											? __('Nobody reporting to you has an appraisal for the selected period')
											: __('Nobody stands directly in {0} — look inside the departments above', [
													treeNodeLabel,
											  ])
									"
								/>
							</template>
						</GDataTable>
						<span class="flex items-center gap-1.5 text-kra-label text-ink-600 mt-3">
							<Lock class="h-3 w-3 flex-none" />
							{{ __("Read-only. Scores cannot be changed from here.") }}
						</span>
					</div>
				</template>
			</div>
		</template>
	</BaseLayout>
</template>

<script setup>
import { ChevronRight, Lock } from "lucide-vue-next"
import GProgressRing from "@/components/glass/GProgressRing.vue"
import GBadge from "@/components/glass/GBadge.vue"
import { computed, inject, nextTick, ref, watch } from "vue"
import { createResource, LoadingIndicator } from "frappe-ui"

import BaseLayout from "@/components/BaseLayout.vue"
import GEmptyState from "@/components/glass/GEmptyState.vue"
import GSkeleton from "@/components/glass/GSkeleton.vue"
import GSegmented from "@/components/glass/GSegmented.vue"
import GDataTable from "@/components/glass/GDataTable.vue"
import ResourceError from "@/components/ResourceError.vue"
import KpiDetail from "@/views/kpi/KpiDetail.vue"
import { canViewTeamKpi, departmentKpi, employeeKpi, teamKpi } from "@/data/kpi"

const __ = inject("$translate")

// Sentinel understood by the API: average across every cycle of the year.
const ALL_CYCLES = "_all"

// Segmented control keys double as labels; GSegmented translates bare strings.
const MINE = "My KPI"
// The second tab is NAMED FOR THE SCOPE IT SHOWS. A manager's scope is the
// people who report to them, so "Team KPI" is honest there; the CEO's and HR's
// is the whole organisation, and calling that "Team" understates it badly
// enough that somebody would go looking for a wider view that already exists.
// canViewTeamKpi returns the tier ("manager" | "ceo" | "hr") or nothing.
const TEAM = "Team KPI"
const ALL = "All KPI"
const isManagerTier = computed(() => canViewTeamKpi.data === "manager")
const teamTabLabel = computed(() => (isManagerTier.value ? TEAM : ALL))
const TAB_BUTTONS = computed(() => [MINE, teamTabLabel.value]) // __("My KPI"), __("Team KPI"), __("All KPI")
const activeTab = ref(MINE)

const selectedYear = ref(null)
const selectedCycle = ref(null)

const dashboard = createResource({
	url: "hrms.api.kpi.get_my_kpi_dashboard",
	auto: true,
	onSuccess(data) {
		console.info("[MyKPI] dashboard loaded:", {
			year: data.selected_year,
			cycle: data.selected_cycle,
			cycles: data.cycles?.length,
		})
		selectedYear.value = data.selected_year
		selectedCycle.value = data.selected_cycle
	},
})

const years = computed(() => dashboard.data?.years || [])
const cycles = computed(() => dashboard.data?.cycles || [])

function refetch() {
	dashboard.submit({ year: selectedYear.value, cycle: selectedCycle.value })
}

function onYearChange() {
	// Switching year starts from the yearly average, then the user can
	// narrow down to a single cycle of that year.
	selectedCycle.value = ALL_CYCLES
	refetch()
}

const current = computed(() => dashboard.data?.current)

// ————— TEAM KPI (CEO by designation, or HR by role; read-only) —————
// The tab is only drawn when canViewTeamKpi says so, and the endpoint refuses
// anyone else, so no employee list is ever fetched for an ordinary user.
const teamYear = ref(null)
const teamCycle = ref(ALL_CYCLES)
const teamDepartment = ref("")
const teamCompany = ref("")

// Whose detail is open, if anyone. Cleared when the tab changes, so a name from
// one scope never survives into another.
const openedName = ref(null)
const openedEmployee = ref(null)
const detailRef = ref(null)

// The payload names its own subject, so identity is the honest test. Truthiness
// is not: the resource is a singleton and keeps the previous subject's data
// through the next fetch.
const openedDetail = computed(() =>
	employeeKpi.data?.employee?.name === openedEmployee.value ? employeeKpi.data : null
)

async function openEmployee(row) {
	openedName.value = row.employee_name
	openedEmployee.value = row.employee
	console.info("[TeamKPI] opening detail for", row.employee)
	employeeKpi.submit({ employee: row.employee, year: teamYear.value, cycle: teamCycle.value })
	// The button that was activated unmounts with the table. Without this,
	// focus falls to <body>: a keyboard user re-tabs from the top of the
	// document and a screen-reader user is told nothing, still "inside" a
	// table that no longer exists.
	await nextTick()
	detailRef.value?.focus()
}

async function closeEmployee({ restoreFocus = false } = {}) {
	openedName.value = null
	openedEmployee.value = null
	if (!restoreFocus) return
	// Returning from the detail has the mirror problem: the back button
	// unmounts too. Land on the Scores heading, which is where the list starts.
	await nextTick()
	scoresHeadingEl.value?.focus()
}

const scoresHeadingEl = ref(null)

// CEO and HR walk the department TREE; a manager gets the flat list of their
// reports, because their scope is people rather than org structure. Two
// fetchers, one page — the tier decides which one is in play.
const treeNode = ref(null)

function fetchTree() {
	console.info("[TeamKPI] department node", treeNode.value || "root")
	departmentKpi.submit({
		parent: treeNode.value,
		year: teamYear.value,
		cycle: teamCycle.value,
		company: teamCompany.value || null,
	})
}

const nodeEl = ref(null)

async function openDepartment(name) {
	closeEmployee()
	treeNode.value = name
	fetchTree()
	// The button that was activated unmounts with its block — a leaf has no
	// Departments table, and the root crumb is not a button. Without this,
	// focus falls to <body> on every drill and a screen-reader user is told
	// nothing. The current crumb always exists, so it is the anchor.
	await nextTick()
	nodeEl.value?.[0]?.focus?.() ?? nodeEl.value?.focus?.()
}

function openDepartmentRow(row) {
	openDepartment(row.name)
}

const treeCrumbs = computed(() => departmentKpi.data?.breadcrumb || [])
const treeNodeLabel = computed(() => departmentKpi.data?.node?.label || "")
const atTreeRoot = computed(() => Boolean(departmentKpi.data?.node?.is_root))
const treeDepartments = computed(() => departmentKpi.data?.departments || [])

const DEPARTMENT_COLUMNS = computed(() => [
	{ key: "label", label: __("Department"), action: true },
	{ key: "headcount", label: __("People"), numeric: true },
	{ key: "score", label: __("Average"), numeric: true },
])

const treeDepartmentRows = computed(() =>
	treeDepartments.value.map((d) => ({
		// carried so a row can open the node; no column renders it
		name: d.name,
		label: d.label,
		headcount: d.headcount,
		score: score1(d.average_score),
	}))
)

function fetchTeam() {
	console.info("[TeamKPI] loading", {
		year: teamYear.value,
		cycle: teamCycle.value,
		company: teamCompany.value || null,
		department: teamDepartment.value || null,
	})
	if (!isManagerTier.value) return fetchTree()
	teamKpi.submit({
		year: teamYear.value,
		cycle: teamCycle.value,
		company: teamCompany.value || null,
		department: teamDepartment.value || null,
	})
}

// Switching year starts from that year's average across cycles, and clears the
// narrowing filters — a department that exists in 2026 may have nobody
// appraised in 2025, and a filter silently pointing at an empty set reads as
// broken data rather than as a filter.
function onTeamYearChange() {
	teamCycle.value = ALL_CYCLES
	teamCompany.value = ""
	teamDepartment.value = ""
	fetchTeam()
}

// Departments carry their company's suffix ("Sales - WWSB"), so a department
// held over from another company can never match. The cycle is cleared for the
// same reason in spirit: `cycles` is deliberately NOT narrowed by company (that
// would strand the year), so a cycle belonging to the company you just left
// stays selectable and returns nothing, with both selectors still reading as if
// they were valid.
function onTeamCompanyChange() {
	teamCycle.value = ALL_CYCLES
	teamDepartment.value = ""
	fetchTeam()
}

// First visit to the tab loads; afterwards the filters drive the fetches.
// Compared against the tab's IDENTITY, never its label. The label is now
// per-tier ("Team KPI" for a manager, "All KPI" for the CEO and HR), and
// testing `tab === TEAM` silently stopped firing for the CEO and HR the moment
// the second label existed — their tab fetched nothing, ever, and there is no
// other trigger: fetchTeam is otherwise reachable only from the filter bar,
// which itself only renders once a fetch has returned. Permanently empty, for
// the two tiers the feature was built for.
//
// Whichever fetcher the tier put in play answers for the shared chrome — the
// filter bar, the hero and the people list all read ONE payload, so they cannot
// end up describing different scopes on the same screen.
//
// DECLARED BEFORE THE WATCHES BELOW, on purpose. `watch(() => teamData.value)`
// runs its getter synchronously at setup to collect dependencies, so with this
// `const` further down the getter hit the temporal dead zone: setup threw
// "Cannot access 'teamData' before initialization", the KPI page never mounted
// its <ion-page>, and Ionic's outlet was left holding a view with no element —
// every later enter/leave errored ("instance.update is not a function") and the
// page looked stuck going back and forth. Pinned by __tests__/Dashboard.test.js.
const teamData = computed(() => (isManagerTier.value ? teamKpi.data : departmentKpi.data))
const teamResource = computed(() => (isManagerTier.value ? teamKpi : departmentKpi))

watch(activeTab, (tab) => {
	closeEmployee()
	if (tab !== MINE && !teamData.value && !teamResource.value.loading) fetchTeam()
})

// A stale active tab must not survive a tier change. TAB_BUTTONS is a computed
// now, so a cached tier that hydrates as one value and refetches as another can
// leave activeTab holding a label the segmented control no longer offers —
// nothing selected, no way back. RequestPanel carries the same clamp for the
// same reason, pinned by tests/request-panel-tabs.test.mjs.
watch(TAB_BUTTONS, (tabs) => {
	if (!tabs.includes(activeTab.value)) activeTab.value = MINE
})

watch(
	() => teamData.value,
	(data) => {
		if (!data) return
		teamYear.value = data.selected_year
		teamCycle.value = data.selected_cycle
	}
)

const teamYears = computed(() => teamData.value?.years || [])
const teamCycles = computed(() => teamData.value?.cycles || [])
// only the manager tier still uses a department SELECTOR; the tree walks instead
const teamDepartments = computed(
	() => (isManagerTier.value ? teamKpi.data?.departments : []) || []
)
const teamCompanies = computed(() => teamData.value?.companies || [])
const teamSummary = computed(() => teamData.value?.summary)

// What the filters currently select, as one string, read by BOTH the visible
// eyebrow and the screen-reader status line — one source, so they cannot drift.
// The status line needs it because without it every empty result announced the
// identical "No appraisals here": changing a filter and landing on another
// empty set changed nothing and announced nothing, so a listener could not tell
// the fetch had happened at all.
//
// The status line is silenced while loading. scopeLabel tracks the filter refs,
// which move the instant the select changes, so an ungated region announced the
// NEW scope beside the OLD numbers and then announced again when data landed —
// the same defect the badge-row skeleton fixes visually, moved into the audio.
const scopeLabel = computed(() =>
	[
		// Year first, matching My KPI's eyebrow. It was missing, and it is the
		// filter always on screen: two empty years in a row from the default
		// scope produced a byte-identical string, so the fetch announced nothing.
		teamYear.value,
		// A manager has no company or department control, so naming either would
		// read back a choice they were never offered.
		isManagerTier.value ? __("My team") : null,
		!isManagerTier.value && teamCompanies.value.length > 1
			? teamCompany.value || __("All companies")
			: null,
		// The NODE, for the tree tier. This read `teamDepartment`, which the tree
		// never writes — so at every depth the page announced "All departments"
		// while the user stood inside Sales East. Not merely unannounced: the
		// only announcement it made was false, and it asserted a scope the
		// tables underneath it did not show.
		isManagerTier.value
			? teamDepartment.value || __("All departments")
			: departmentKpi.data?.node?.label || __("All departments"),
		teamCycle.value === ALL_CYCLES ? __("All Appraisal Cycles") : teamCycle.value,
	]
		.filter(Boolean)
		.join(" · ")
)

const TEAM_COLUMNS = computed(() => [
	{ key: "employee_name", label: __("Employee"), action: true },
	{ key: "department", label: __("Department") },
	{ key: "score", label: __("Score"), numeric: true },
	{ key: "grade", label: __("Grade"), numeric: true },
])

// GDataTable renders raw cell values, so formatting happens here rather than in
// the table — it stays a dumb, solid surface (§6.3).
//
// ONE fixed decimal, not formatScore: that helper drops a trailing ".0" for the
// hero's prose context, which in a right-aligned tabular-nums column ships
// "91", "74.2", "48" — ragged, defeating the whole point of tabular figures in
// a column of numbers people argue about.
const score1 = (value) => (Number(value) || 0).toFixed(1)

const teamRows = computed(() =>
	(isManagerTier.value ? teamKpi.data?.rows || [] : departmentKpi.data?.people || []).map(
		(row) => ({
			// carried so a row can open the person; never rendered — no column names it
			employee: row.employee,
			employee_name: row.employee_name,
			department: row.department || __("No department"),
			score: score1(row.total_score),
			grade: row.grade || "—",
		})
	)
)
</script>

<style scoped>
/* Modernist filter selects: surface fill, hairline border, square. */
/* Programmatic focus target when the detail closes — no ring, same reasoning
   as KpiDetail's heading. */
.kpi-scores-heading:focus {
	outline: none;
}

.kpi-filter {
	background-color: var(--g-glass-fill-fallback);
	border: 1px solid var(--g-hair);
	border-radius: 0;
	color: var(--g-ink);
	font-size: 13px;
	font-weight: 600;
	padding: 8px 32px 8px 12px;
	min-width: 150px;
	/* A select sizes to its widest option, and these are user-named masters — a
	   company name or a suffixed department ("Human Resources - VRFC") can
	   exceed a 375px content box and push the whole page sideways.
	   max-width ALONE is a no-op here: the percentage resolves against the
	   field wrapper, and that wrapper is a flex item whose automatic minimum
	   size IS the select's min-content width. The wrapper is sized by the
	   select and the select is capped by the wrapper — circular. `min-w-0` on
	   every wrapper breaks that cycle; the two go together.
	   The ellipsis is progressive enhancement only: Chromium draws it on a
	   native select, Gecko and WebKit hard-clip with no glyph, so it must never
	   be the only thing signalling truncation. */
	max-width: 100%;
	text-overflow: ellipsis;
	/* §14.1. Three of these now sit side by side on a phone; at 13px type and
	   8px padding the real target was 34px. */
	min-height: var(--g-touch-target-min);
}
/* The focus ring is NOT redeclared here. This block used to end
   `outline: none; box-shadow: none`, which — being scoped — outranked
   `.g-focusable:focus-visible` by data-v specificity and silently deleted the
   §14.3 two-tone ring from every filter on this page. Same specificity trap
   GSegmented.vue records for its deleted min-height. The border tint stays as
   a second, redundant cue. */
.kpi-filter:focus-visible {
	border-color: var(--g-accent-ink);
}
</style>
