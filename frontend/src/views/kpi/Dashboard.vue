<template>
	<BaseLayout :pageTitle="__('My KPI')">
		<template #body>
			<div class="flex flex-col w-full max-w-3xl mx-auto px-4 py-7 gap-8 lg:px-7 lg:py-9">
				<ResourceError :resource="dashboard" what="your KPI dashboard" />
				<!-- Filters -->
				<div
					v-if="years.length"
					class="flex flex-wrap items-end gap-x-6 gap-y-3 border-b-2 border-divider pb-5"
				>
					<div class="flex flex-col gap-1.5">
						<label class="g-eyebrow" for="kpi-year-filter">{{ __("Year") }}</label>
						<select
							id="kpi-year-filter"
							v-model="selectedYear"
							@change="onYearChange"
							class="kpi-filter"
						>
							<option v-for="y in years" :key="y" :value="y">{{ y }}</option>
						</select>
					</div>
					<div class="flex flex-col gap-1.5">
						<label class="g-eyebrow" for="kpi-cycle-filter">
							{{ __("Appraisal cycle") }}
						</label>
						<select
							id="kpi-cycle-filter"
							v-model="selectedCycle"
							@change="refetch"
							class="kpi-filter"
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
									:score="Number(current.total_score) || 0"
									:max="100"
									:label="__('Overall score')"
								/>
							</div>
						</div>

						<!-- Score trend -->
						<div v-if="trend.length > 1">
							<div
								class="g-eyebrow mb-2.5"
							>
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
							<div
								class="g-eyebrow mb-2.5"
							>
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
							<span class="block text-kra-label text-ink-600 mt-3">
								🔒 {{ __("You can only see your own scores") }}
							</span>
						</div>
					</div>
				</template>

				<GEmptyState
					v-else-if="dashboard.data"
					:title="__('No appraisals yet')"
					:body="__('Your KPI appears here once a review cycle opens for you')"
				/>
			</div>
		</template>
	</BaseLayout>
</template>

<script setup>
import GProgressRing from "@/components/glass/GProgressRing.vue"
import GBadge from "@/components/glass/GBadge.vue"
import { computed, inject, ref } from "vue"
import { createResource } from "frappe-ui"

import BaseLayout from "@/components/BaseLayout.vue"
import GEmptyState from "@/components/glass/GEmptyState.vue"
import ResourceError from "@/components/ResourceError.vue"

const __ = inject("$translate")

// Sentinel understood by the API: average across every cycle of the year.
const ALL_CYCLES = "_all"

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
}
.kpi-filter:focus {
	border-color: var(--g-accent-ink);
	outline: none;
	box-shadow: none;
}
</style>
