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

					<template v-if="current">
						<div class="contents">
							<!-- Hero: overall score -->
							<div>
								<div class="g-eyebrow">
									<template v-if="current.is_average">
										{{ selectedYear }} · {{ __("All Appraisal Cycles") }}
									</template>
									<template v-else> {{ __("Appraisal cycle") }} · {{ current.cycle }} </template>
								</div>
								<div class="flex items-center justify-between mt-3 border-t-2 border-divider pt-4">
									<div class="flex flex-col gap-2">
										<div class="font-sans font-extrabold text-clock leading-none tabular-nums">
											{{ formatScore(current.total_score)
											}}<span class="text-button-label text-ink-500 font-normal"> / 100</span>
										</div>
										<div class="flex items-center gap-2.5">
											<GBadge v-if="current.grade" variant="accent">
												{{ current.grade }}
											</GBadge>
											<GBadge v-if="current.is_average" variant="accent">
												{{ __("Avg of {0} cycles", [current.cycles_count]) }}
											</GBadge>
											<span
												v-if="delta !== null"
												class="text-xs font-sans font-extrabold text-ink-700"
											>
												{{ delta >= 0 ? "+" : "−" }}{{ Math.abs(delta).toFixed(1) }}
												{{ __("vs last cycle") }}
											</span>
										</div>
									</div>
									<!-- §10.1 #9 geometry (88×88, r38, circumference 238.8) and, per §6.3,
								     a SOLID track: a performance score argued about in a
								     review must not be read through a moving tint. The
								     hand-rolled ring this replaces was 84×84 with an
								     --ink3 track. -->
									<GProgressRing
										:score="Math.round(Number(current.total_score) || 0)"
										:max="100"
										:label="__('Overall score')"
									/>
								</div>
							</div>

							<!-- Score trend -->
							<div v-if="trend.length > 1">
								<div class="g-eyebrow mb-2.5">
									{{ __("Score trend") }}
								</div>
								<div class="border-t-2 border-divider pt-3">
									<svg :viewBox="`0 0 320 110`" class="w-full">
										<line
											v-for="g in [0, 50, 100]"
											:key="g"
											:y1="trendY(g)"
											:y2="trendY(g)"
											x1="24"
											x2="312"
											stroke="currentColor"
											class="text-ink-300"
											stroke-width="1"
										/>
										<text
											v-for="g in [0, 50, 100]"
											:key="'l' + g"
											x="20"
											:y="trendY(g) + 3"
											text-anchor="end"
											fill="currentColor"
											class="text-ink-500"
											font-size="9"
										>
											{{ g }}
										</text>
										<polyline
											fill="none"
											stroke="currentColor"
											class="text-inkbase"
											stroke-width="2"
											:points="trendPoints"
										/>
										<g v-for="(p, i) in trend" :key="'p' + i">
											<circle
												:cx="trendX(i)"
												:cy="trendY(p.total_score)"
												r="3"
												fill="currentColor"
												class="text-inkbase"
											/>
											<text
												:x="trendX(i)"
												y="106"
												text-anchor="middle"
												fill="currentColor"
												class="text-ink-500"
												font-size="9"
											>
												{{ p.cycle }}
											</text>
										</g>
									</svg>
								</div>
							</div>
						</div>

						<div class="contents">
							<!-- KRA list -->
							<div>
								<div class="g-eyebrow mb-2.5">
									{{ __("My KRAs") }}
								</div>
								<div class="border-t-2 border-divider">
									<div
										v-for="(row, idx) in current.kras"
										:key="idx"
										class="border-b border-hair flex flex-col gap-1.5 py-3"
									>
										<div class="flex items-center justify-between gap-2">
											<span class="font-sans font-semibold text-button-label">
												{{ row.kra }}
											</span>
											<GBadge v-if="row.per_weightage" variant="neutral" class="whitespace-nowrap">
												{{ formatScore(row.per_weightage) }}%
											</GBadge>
										</div>
										<span v-if="row.kpi" class="text-xs text-ink-600 leading-4">
											{{ row.kpi }}
										</span>
										<div class="flex items-center gap-2.5">
											<div class="g-kra__bar flex-1">
												<div
													class="g-kra__fill"
													:style="{ width: `${Math.min(barValue(row), 100)}%` }"
												/>
											</div>
											<span
												class="font-sans font-extrabold text-kra-label tabular-nums w-12 text-right"
											>
												{{ formatScore(barValue(row)) }}%
											</span>
										</div>
										<div class="flex flex-wrap gap-x-3 text-kra-label text-ink-500">
											<span v-if="row.target">
												{{ __("Target") }} {{ formatNumber(row.target) }}
											</span>
											<span v-if="row.actual"
												>{{ __("Actual") }} {{ formatNumber(row.actual) }}</span
											>
											<span v-if="row.weighted_score">
												{{ __("Weighted") }} {{ formatScore(row.weighted_score) }}
											</span>
										</div>
									</div>
									<GEmptyState
										v-if="!current.kras.length"
										:title="__('No KRAs in this appraisal')"
										:body="__('Your manager sets these when the cycle opens')"
									/>
								</div>
							</div>

							<!-- Feedback -->
							<div>
								<div class="border-t-2 border-divider">
									<div class="border-b border-hair flex items-center justify-between py-3">
										<span class="text-sm">
											{{
												current.is_average
													? __("Feedback received this year")
													: __("Feedback received this cycle")
											}}
										</span>
										<span class="font-sans font-extrabold text-base tabular-nums">
											{{ dashboard.data.feedback.count }}
										</span>
									</div>
								</div>
								<span class="flex items-center gap-1.5 text-kra-label text-ink-600 mt-3">
									<FeatherIcon name="lock" class="h-3 w-3 flex-none" />
									{{ __("You can only see your own scores") }}
								</span>
							</div>
						</div>
					</template>

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

				<!-- TEAM KPI — read-only, CEO designation only. The v-if is a
				     convenience, not the fence: hrms.api.kpi.get_team_kpi re-checks
				     the designation and refuses everyone else. -->
				<template v-else>
					<ResourceError :resource="teamKpi" what="the team KPI view" />

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
						     between: a one-option selector is not a control. -->
						<div v-if="teamCompanies.length > 1" class="flex min-w-0 flex-col gap-1.5">
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
						<div class="flex min-w-0 flex-col gap-1.5">
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
					<div v-if="teamKpi.data && teamYears.length && !teamKpi.error">
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
									v-if="teamKpi.loading"
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
								<GSkeleton v-if="teamKpi.loading" width="180px" height="20px" />
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
								:loading="teamKpi.loading"
							/>
						</div>
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
							teamKpi.error || teamKpi.loading
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

					<div v-if="!teamKpi.error">
						<div class="g-eyebrow mb-2.5">{{ __("Scores") }}</div>
						<GDataTable
							:columns="TEAM_COLUMNS"
							:rows="teamRows"
							:caption="__('Team KPI scores')"
							:loading="teamKpi.loading"
						>
							<template #empty>
								<GEmptyState
									:title="__('No appraisals here')"
									:body="__('Nobody in this department has an appraisal for the selected period')"
								/>
							</template>
						</GDataTable>
						<span class="flex items-center gap-1.5 text-kra-label text-ink-600 mt-3">
							<FeatherIcon name="lock" class="h-3 w-3 flex-none" />
							{{ __("Read-only. Scores cannot be changed from here.") }}
						</span>
					</div>
				</template>
			</div>
		</template>
	</BaseLayout>
</template>

<script setup>
import GProgressRing from "@/components/glass/GProgressRing.vue"
import GBadge from "@/components/glass/GBadge.vue"
import { computed, inject, ref, watch } from "vue"
import { createResource, FeatherIcon, LoadingIndicator } from "frappe-ui"

import BaseLayout from "@/components/BaseLayout.vue"
import GEmptyState from "@/components/glass/GEmptyState.vue"
import GSkeleton from "@/components/glass/GSkeleton.vue"
import GSegmented from "@/components/glass/GSegmented.vue"
import GDataTable from "@/components/glass/GDataTable.vue"
import ResourceError from "@/components/ResourceError.vue"
import { canViewTeamKpi, teamKpi } from "@/data/kpi"

const __ = inject("$translate")

// Sentinel understood by the API: average across every cycle of the year.
const ALL_CYCLES = "_all"

// Segmented control keys double as labels; GSegmented translates bare strings.
const MINE = "My KPI"
const TEAM = "Team KPI"
const TAB_BUTTONS = [MINE, TEAM] // __("My KPI"), __("Team KPI")
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
const trend = computed(() => dashboard.data?.history || [])

const delta = computed(() => {
	const prev = dashboard.data?.previous_score
	if (prev === null || prev === undefined || !current.value) return null
	return current.value.total_score - prev
})

// ring circumference: 2 * PI * 34 ≈ 213.6

function formatScore(value) {
	return Number(value || 0)
		.toFixed(1)
		.replace(/\.0$/, "")
}

// Thousands-separated target/actual (e.g. 23083692 -> "23,083,692").
// Non-numeric values (rare free-text targets) pass through untouched.
function formatNumber(value) {
	const n = Number(value)
	if (!Number.isFinite(n)) return value
	return n.toLocaleString("en-US", { maximumFractionDigits: 2 })
}

// KRA rows may be achievement-based (auto) or manager-rated (manual)
function barValue(row) {
	if (row.achievement) return Number(row.achievement)
	if (row.goal_completion) return Number(row.goal_completion)
	if (row.manager_rating) return (Number(row.manager_rating) / 5) * 100
	return 0
}

function trendX(i) {
	const count = Math.max(trend.value.length - 1, 1)
	return 24 + (i * (312 - 24)) / count
}

function trendY(score) {
	// plot area: y 8 (score 100) to y 92 (score 0)
	return 92 - (Math.min(Math.max(score, 0), 100) / 100) * 84
}

const trendPoints = computed(() =>
	trend.value.map((p, i) => `${trendX(i)},${trendY(p.total_score)}`).join(" ")
)

// ————— TEAM KPI (CEO by designation, or HR by role; read-only) —————
// The tab is only drawn when canViewTeamKpi says so, and the endpoint refuses
// anyone else, so no employee list is ever fetched for an ordinary user.
const teamYear = ref(null)
const teamCycle = ref(ALL_CYCLES)
const teamDepartment = ref("")
const teamCompany = ref("")

function fetchTeam() {
	console.info("[TeamKPI] loading", {
		year: teamYear.value,
		cycle: teamCycle.value,
		company: teamCompany.value || null,
		department: teamDepartment.value || null,
	})
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
watch(activeTab, (tab) => {
	if (tab === TEAM && !teamKpi.data && !teamKpi.loading) fetchTeam()
})

watch(
	() => teamKpi.data,
	(data) => {
		if (!data) return
		teamYear.value = data.selected_year
		teamCycle.value = data.selected_cycle
	}
)

const teamYears = computed(() => teamKpi.data?.years || [])
const teamCycles = computed(() => teamKpi.data?.cycles || [])
const teamDepartments = computed(() => teamKpi.data?.departments || [])
const teamCompanies = computed(() => teamKpi.data?.companies || [])
const teamSummary = computed(() => teamKpi.data?.summary)

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
		teamCompanies.value.length > 1 ? teamCompany.value || __("All companies") : null,
		teamDepartment.value || __("All departments"),
		teamCycle.value === ALL_CYCLES ? __("All Appraisal Cycles") : teamCycle.value,
	]
		.filter(Boolean)
		.join(" · ")
)

const TEAM_COLUMNS = computed(() => [
	{ key: "employee_name", label: __("Employee") },
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
	(teamKpi.data?.rows || []).map((row) => ({
		employee_name: row.employee_name,
		department: row.department || __("No department"),
		score: score1(row.total_score),
		grade: row.grade || "—",
	}))
)
</script>

<style scoped>
/* Modernist filter selects: surface fill, hairline border, square. */
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
