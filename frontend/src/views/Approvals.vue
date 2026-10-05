<template>
	<BaseLayout :pageTitle="__('Approvals')">
		<template #body>
			<!-- Everything waiting on YOUR decision (audit-flows 4B; owner ruling
			     23 Sep: approvals appear only where they can be done), GROUPED so a
			     long queue reads at a glance (owner-approved design, 23 Sep): Yours
			     first, then Other teams you may act for; department, then kind; one
			     line per person; five lines, then "See all"; never an endless list
			     (NN/g infinite scrolling; Baymard "load more"). Every request still
			     opens the same sheet that decides it. -->
			<GPullRefresh @refresh="refresh" />
			<div
				class="flex flex-col gap-4 px-4 pt-6 pb-8 w-full max-w-content-column-lg mx-auto lg:py-7"
			>
				<ResourceError :resource="waiting" what="your approvals" />

				<!-- As tall as the page it becomes when requests wait (the summary
				     line, a group heading and its first row), so the queue arriving
				     does not push "already answered" down (scroll-and-shift audit,
				     29 Sep 2026: the approval line now routes more to approvers). -->
				<template v-if="waiting.loading && !waiting.data">
					<p class="g-form-footer" aria-hidden="true">&nbsp;</p>
					<!-- the "Yours" section it becomes: 144 pt, measured 29 Sep 2026 -->
					<div class="g-approvals__placeholder">
						<GListPanel loading :rows="2" />
					</div>
				</template>

				<template v-else-if="!waiting.error">
					<!-- The approver's own deadline, said plainly (HR, 4 Oct 2026: "make sure the
					     approver notices and does their job"). A banner only: it blocks nothing
					     and forces nothing (owner, 5 Oct). -->
					<GBanner v-if="headline" variant="warning" data-testid="approvals-banner">
						<p class="m-0 font-semibold">
							{{
								__("{0} waiting. Oldest since {1}.", [
									headline.count,
									$dayjs(headline.oldest).format("D MMM"),
								])
							}}
						</p>
						<p class="m-0 text-caption text-ink-600">
							{{ __("Staff attendance and pay wait on your decision.") }}
						</p>
					</GBanner>
					<p v-if="rows.length" class="g-form-footer">
						{{ summary }}
					</p>
					<div v-if="rows.length" class="flex items-center justify-between gap-3">
						<div class="g-approvals__chips" role="group" :aria-label="__('Filter by type')">
							<button
								v-for="chip in chips"
								:key="chip.key"
								type="button"
								class="g-focusable g-approvals__chip"
								:class="{ 'g-approvals__chip--on': kindFilter === chip.key }"
								:aria-pressed="String(kindFilter === chip.key)"
								@click="kindFilter = chip.key"
							>
								{{ chip.key ? __(chip.label) : __("All") }} · {{ chip.count }}
							</button>
						</div>
						<button
							type="button"
							class="g-focusable g-approvals__select"
							@click="toggleSelectMode"
						>
							{{ selectMode ? __("Done") : __("Select") }}
						</button>
					</div>
					<p
						v-if="selectMode && nothingTickable(visibleRows)"
						class="text-caption text-ink-600 m-0"
					>
						{{ __("These are approved one by one. Tap one to open it.") }}
					</p>
					<div v-if="selectMode && pickable.length" class="flex items-center">
						<GCheckbox
							:model-value="allState === 'all'"
							:label="__('Select all shown')"
							@update:model-value="ticked = toggleAll(ticked, visibleRows)"
						/>
						<span class="text-caption text-ink-600 ml-auto">
							{{ ticked.size }} / {{ pickable.length }}
						</span>
					</div>
					<!-- The same 51 pt row as the skeleton above (alpha.8 r3: three
					     skeleton rows collapsing to one grey line moved the page
					     132 pt; alpha.9 D5: nothing loose). -->
					<GListPanel v-if="!rows.length">
						<GListRow
							:label="__('Nothing is waiting on you.')"
							:tint="TILE.neutral"
							:tappable="false"
						>
							<template #icon>
								<CircleCheckBig class="g-row-icon" />
							</template>
						</GListRow>
					</GListPanel>

					<!-- YOURS: sent to you to decide -->
					<section v-if="groups.yours.count" class="flex flex-col gap-3">
						<h2 class="g-eyebrow">{{ __("Yours") }} · {{ groups.yours.count }}</h2>
						<!-- ONE panel for the section, groups separated by captions (§15.2:
						     a grouped list is flattened into one surface, as the balance
						     grid and issue list are). -->
						<GListPanel>
							<template v-for="dept in groups.yours.departments" :key="dept.key">
								<p class="g-approvals__dept text-caption text-ink-600">
									{{ dept.name || __("No department") }} · {{ dept.count }}
								</p>
								<template v-for="kind in dept.kinds" :key="`${dept.key}:${kind.key}`">
									<p class="g-approvals__kind text-caption text-ink-600">
										{{ __(kind.kind) }} · {{ kind.count }}
									</p>
									<!-- A decided person leaves and the list closes the gap,
									     instead of the rows jumping when the queue reloads
									     (alpha.13). -->
									<TransitionGroup name="g-leave">
										<template
											v-for="person in shown(`${dept.key}:${kind.key}`, kind.people).rows"
											:key="person.key"
										>
											<!-- select mode: one tick per request, so the approver ticks what
											     they mean (a person can have three requests of one kind) -->
											<template v-if="selectMode && person.rows.some(canBulk)">
												<GListRow
													v-for="req in person.rows.filter(canBulk)"
													:key="rowKey(req)"
													:label="`${req.who} · ${[req.when, req.detail]
														.filter(Boolean)
														.join(' · ')}`"
													:sublabel="ageText(req)"
													:chevron="false"
													role="checkbox"
													:aria-checked="String(ticked.has(rowKey(req)))"
													@click="ticked = toggle(ticked, req)"
												>
													<template #icon>
														<span
															class="g-approvals__tick"
															:class="{ 'g-approvals__tick--on': ticked.has(rowKey(req)) }"
															aria-hidden="true"
														>
															<Check v-if="ticked.has(rowKey(req))" class="g-row-icon" />
														</span>
													</template>
													<template #badge>
														<span
															class="g-approvals__age"
															:class="`g-approvals__age--${tone(req)}`"
															>{{ ageWords(req) }}</span
														>
													</template>
												</GListRow>
											</template>
											<GListRow
												v-else
												:label="personLine(person, __)"
												:sublabel="personWhen(person)"
												@click="openPerson(person)"
											>
												<template #badge>
													<span
														class="g-approvals__age"
														:class="`g-approvals__age--${tone(person.rows[0])}`"
														>{{ ageWords(person.rows[0]) }}</span
													>
												</template>
											</GListRow>
										</template>
									</TransitionGroup>
									<GroupMore
										:page="shown(`${dept.key}:${kind.key}`, kind.people)"
										@all="expand(`${dept.key}:${kind.key}`)"
										@more="more(`${dept.key}:${kind.key}`)"
									/>
								</template>
							</template>
						</GListPanel>
					</section>

					<!-- OTHER TEAMS: someone else approves; you may step in -->
					<section v-if="groups.other.count" class="flex flex-col gap-3">
						<!-- A heading like "Yours", so heading navigation finds it; the
						     button inside it is the disclosure (WAI-ARIA APG). -->
						<h2 class="m-0">
							<button
								type="button"
								class="g-focusable g-approvals__toggle"
								:aria-expanded="String(otherOpen)"
								aria-controls="approvals-other-teams"
								@click="otherOpen = !otherOpen"
							>
								<span class="g-eyebrow">{{ __("Other teams") }} · {{ groups.other.count }}</span>
								<span class="text-caption text-ink-600">{{
									otherOpen ? __("Hide") : __("Show")
								}}</span>
							</button>
						</h2>
						<div v-show="otherOpen" id="approvals-other-teams" class="flex flex-col gap-3">
							<GListPanel>
								<template v-for="team in groups.other.teams" :key="team.key">
									<p class="g-approvals__kind text-caption text-ink-600">
										{{
											[
												team.name || __("No department"),
												team.approverName ? __("{0}'s team", [team.approverName]) : "",
												team.count,
											]
												.filter(Boolean)
												.join(" · ")
										}}
									</p>
									<GListRow
										v-for="person in shown(team.key, team.people).rows"
										:key="person.key"
										:label="personLine(person, __)"
										:sublabel="`${__(person.kind)} · ${personWhen(person)}`"
										@click="openPerson(person)"
									/>
									<GroupMore
										:page="shown(team.key, team.people)"
										@all="expand(team.key)"
										@more="more(team.key)"
									/>
								</template>
							</GListPanel>
						</div>
					</section>

					<p v-if="waiting.data?.capped" class="text-caption text-ink-600">
						{{ __("Showing the oldest first. More are waiting.") }}
					</p>
				</template>

				<!-- Ruling 2 (23 Sep): what you already answered stays reachable,
				     worded for what is behind it: requests on the Requests page,
				     check-ins in a sheet here. -->
				<GListPanel v-if="isApprover.data">
					<GListRow :label="requestsAnsweredLabel" @click="openAnsweredRequests" />
					<GListRow :label="answeredLabel" @click="openAnswered" />
				</GListPanel>
			</div>

			<!-- One person's requests of one kind: each opens the deciding sheet. -->
			<GModal :is-open="!!personOpen" :title="personOpen?.who" @did-dismiss="personOpen = null">
				<GListPanel v-if="personOpen">
					<GListRow
						v-for="row in personOpen.rows"
						:key="`${row.doctype}:${row.name}`"
						:label="`${__(row.kind)} · ${row.who}`"
						:sublabel="rowLine(row)"
						@click="open(row)"
					/>
				</GListPanel>
			</GModal>

			<GModal :is-open="answeredOpen" :title="answeredLabel" @did-dismiss="answeredOpen = false">
				<div class="flex flex-col gap-3 px-4 pb-8">
					<GListPanel v-if="decided.loading && !decided.data" loading />
					<ResourceError v-else-if="decided.error" :resource="decided" what="your answers" />
					<GListPanel v-else-if="decided.data?.length">
						<GListRow
							v-for="req in decided.data"
							:key="req.name"
							:label="`${req.employee_name || req.employee} · ${__(req.status)}`"
							:sublabel="answeredLine(req)"
						/>
					</GListPanel>
					<p v-else class="text-caption text-ink-600">{{ __("Nothing answered yet.") }}</p>
				</div>
			</GModal>

			<GModal :is-open="!!selected" @did-dismiss="close">
				<CheckinDecisionSheet
					v-if="selected?.doctype === 'Remote Checkin Request'"
					:row="selected.row"
					@decided="close"
				/>
				<RequestActionSheet
					v-else-if="selected"
					:fields="REQUEST_SUMMARY_FIELDS[selected.doctype]"
					v-model="selected"
				/>
			</GModal>

			<!-- The bar the approver acts from: how many are ticked, and one button. -->
			<div
				v-if="selectMode && ticked.size"
				class="g-approvals__bar"
				role="region"
				:aria-label="__('Approve the ticked requests')"
			>
				<div class="min-w-0">
					<p class="m-0 font-semibold">{{ __("{0} selected", [ticked.size]) }}</p>
					<p class="m-0 text-caption text-ink-600">
						{{ __("Each one is checked before it is approved.") }}
					</p>
				</div>
				<button type="button" class="g-focusable g-approvals__clear" @click="ticked = new Set()">
					{{ __("Clear") }}
				</button>
				<GButton :label="__('Approve {0}', [ticked.size])" @click="startApprove" />
			</div>

			<GModal :is-open="!!sheet" :title="__('Approve')" @did-dismiss="dismissSheet">
				<template v-if="sheet">
					<p v-if="sheet.phase === 'check'" class="text-caption text-ink-600" role="status">
						{{ __("Checking each one…") }}
					</p>
					<!-- A failed check stays here, with the ticks kept and a way to try again: a toast
					     disappears on its own and leaves nothing to press. -->
					<div v-else-if="sheet.phase === 'failed'" class="flex flex-col gap-3" role="alert">
						<p class="m-0 font-semibold">{{ __("Nothing was approved.") }}</p>
						<p class="m-0 text-caption text-ink-600">
							{{ __("Your ticks are kept. Check your connection and try again.") }}
						</p>
						<GButton :label="__('Try again')" @click="startApprove" />
					</div>
					<template v-else>
						<section v-if="sheet.ready.length" class="flex flex-col gap-2">
							<h3 class="g-eyebrow">{{ __("{0} ready", [sheet.ready.length]) }}</h3>
							<GListPanel>
								<GListRow
									v-for="req in sheet.ready"
									:key="rowKey(req)"
									:label="rowLabel(req)"
									:chevron="false"
									:tappable="false"
								/>
							</GListPanel>
						</section>
						<section v-if="sheet.refused.length" class="flex flex-col gap-2">
							<h3 class="g-eyebrow">{{ __("{0} will be refused", [sheet.refused.length]) }}</h3>
							<GListPanel>
								<GListRow
									v-for="req in sheet.refused"
									:key="rowKey(req)"
									:label="rowLabel(req)"
									:sublabel="req.reason"
									:chevron="false"
									:tappable="false"
								/>
							</GListPanel>
							<p class="text-caption text-ink-600">
								{{ __("Refused ones stay in your list. Open one to see what to fix.") }}
							</p>
						</section>
						<GButton
							:label="
								sheet.ready.length
									? __('Approve {0}', [sheet.ready.length])
									: __('Nothing to approve')
							"
							:pending="sheet.phase === 'working'"
							:pending-label="__('Approving…')"
							:disabled="!sheet.ready.length"
							@click="confirmApprove"
						/>
					</template>
				</template>
			</GModal>
		</template>
	</BaseLayout>
</template>

<script setup>
import { computed, defineAsyncComponent, h, inject, reactive, ref, watch } from "vue"
import { useRouter } from "vue-router"
import { createResource } from "frappe-ui"

import BaseLayout from "@/components/BaseLayout.vue"
import CheckinDecisionSheet from "@/components/CheckinDecisionSheet.vue"
import RequestActionSheet from "@/components/RequestActionSheet.vue"
import ResourceError from "@/components/ResourceError.vue"
import GListPanel from "@/components/glass/GListPanel.vue"
import GListRow from "@/components/glass/GListRow.vue"
import GModal from "@/components/glass/GModal.vue"
//: Loaded on first use, not in the first download (alpha.13: Ionic's
//: refresher is 41 KB, and nobody pulls before the page has drawn).
const GPullRefresh = defineAsyncComponent(() => import("@/components/glass/GPullRefresh.vue"))
import { Check, CircleCheckBig } from "lucide-vue-next"
import { TILE } from "@/utils/iconTile"
import { personalCacheKey } from "@/utils/personalCache"
import { REQUEST_SUMMARY_FIELDS } from "@/data/config/requestSummaryFields"
import { decidedForApproverResource } from "@/data/remoteCheckin"
import { isApprover } from "@/data/team"
import { groupApprovals, pageOf, personLine } from "@/utils/approvalGroups"
import {
	afterApprove,
	ageTone,
	allState as allStateOf,
	banner,
	canBulk,
	daysWaiting,
	filterByKind,
	itemsFor,
	keepVisible,
	nothingTickable,
	overCap,
	prune,
	rowKey,
	siteToday,
	toggle,
	toggleAll,
	typeChips,
} from "@/utils/approvalBulk"
import GBanner from "@/components/glass/GBanner.vue"
import GButton from "@/components/glass/GButton.vue"
import GCheckbox from "@/components/glass/GCheckbox.vue"
import { gToast } from "@/components/glass/toast"
import { siteTimeZone } from "@/utils/siteTime"

const __ = inject("$translate")
const router = useRouter()
const $dayjs = inject("$dayjs")

// The server decides who sees what, and which section each row is in: only
// requests routed to the caller, by the same check approval.decide uses
// (hrms/api/approvals_list.py). This page only groups them.
const waiting = createResource({
	url: "hrms.api.approvals_list.get_waiting_for_me",
	// Personal, like every approver-scoped read: without a cache every visit
	// drew three skeleton rows, then collapsed to one line (alpha.8 r3).
	cache: personalCacheKey("nsty:approvals-waiting"),
	auto: true,
})
const rows = computed(() => waiting.data?.rows || [])

// Filter by type (HR, 4 Oct 2026). The chips count what is waiting; the filter narrows what the
// groups below show, so "See all", the group counts and select-all all follow it.
const ticked = ref(new Set())
const kindFilter = ref("")
const chips = computed(() => typeChips(rows.value))
const visibleRows = computed(() => filterByKind(rows.value, kindFilter.value))
const groups = computed(() => groupApprovals(visibleRows.value))
// A tick that is no longer shown (another chip) is dropped: the bar never counts, and Approve
// never sends, a request the approver cannot see ticked (design + code review, 5 Oct 2026).
watch(visibleRows, (list) => (ticked.value = keepVisible(ticked.value, list)))
watch(chips, (list) => {
	// a filter whose last request was decided is gone: fall back to All
	if (kindFilter.value && !list.some((chip) => chip.key === kindFilter.value))
		kindFilter.value = ""
})

const headline = computed(() => banner(rows.value, today()))

// Select mode: tick many, approve once. Check-ins stay one by one (approvalBulk.ONE_BY_ONE).
const selectMode = ref(false)
const pickable = computed(() => visibleRows.value.filter(canBulk))
const allState = computed(() => allStateOf(ticked.value, visibleRows.value))
function toggleSelectMode() {
	selectMode.value = !selectMode.value
	if (!selectMode.value) ticked.value = new Set()
}
// a request that left the list (decided elsewhere, or approved here) is no longer ticked
watch(rows, (list) => (ticked.value = prune(ticked.value, list)))

//: "3 waiting · oldest since 20 Sep" (mockup 4's summary line).
const summary = computed(() => {
	const oldest = [...rows.value].sort((a, b) => (a.modified < b.modified ? -1 : 1))[0]?.modified
	const count = __("{0} waiting", [rows.value.length])
	return oldest ? `${count} · ${__("oldest since {0}", [$dayjs(oldest).format("D MMM")])}` : count
})

// Other teams starts folded when it is long, so your own work stays on top.
const otherOpen = ref(true)
watch(
	() => groups.value.other.startCollapsed,
	(collapsed) => (otherOpen.value = !collapsed),
	{ immediate: true }
)

// Per group: five lines, then "See all"; expanded, twenty per page.
const expanded = reactive({})
function shown(key, lines) {
	return pageOf(lines, { expanded: Boolean(expanded[key]), pages: expanded[key] || 1 })
}
function expand(key) {
	console.info("[Approvals] see all", key)
	expanded[key] = 1
}
function more(key) {
	expanded[key] = (expanded[key] || 1) + 1
}

//: The "See all" / "Show more (N left)" button under a group.
const GroupMore = (props, { emit }) => {
	const page = props.page
	if (page.seeAll) {
		return h(
			"button",
			{ type: "button", class: "g-focusable g-list-more", onClick: () => emit("all") },
			__("See all")
		)
	}
	if (page.left > 0) {
		return h(
			"button",
			{ type: "button", class: "g-focusable g-list-more", onClick: () => emit("more") },
			__("Show more ({0} left)", [page.left])
		)
	}
	return null
}
GroupMore.props = ["page"]
GroupMore.emits = ["all", "more"]

function personWhen(person) {
	return person.oldest ? __("since {0}", [$dayjs(person.oldest).format("D MMM")]) : ""
}

function rowLine(row) {
	return [row.when, row.detail].filter(Boolean).join(" · ")
}

const decided = decidedForApproverResource
const answeredLabel = __("Check-ins you've already answered")
//: Ruling 2 wording: says what is behind it.
const requestsAnsweredLabel = __("Requests you've already answered")
function openAnsweredRequests() {
	console.info("[Approvals] opening answered requests")
	router.push({ name: "Requests", query: { tab: "answered" } })
}
const answeredOpen = ref(false)
function openAnswered() {
	console.info("[Approvals] opening answered check-ins")
	answeredOpen.value = true
	decided.reload()
}
function answeredLine(req) {
	const when = $dayjs(req.checkin_time).format("D MMM, h:mm a")
	return [when, req.approver_remarks].filter(Boolean).join(" · ")
}

// A person line opens their requests of that kind; one request opens straight away.
const personOpen = ref(null)
function openPerson(person) {
	console.info("[Approvals] opening person", person.doctype, person.count)
	if (person.rows.length === 1) return open(person.rows[0])
	personOpen.value = person
}

const selected = ref(null)
function open(row) {
	console.info("[Approvals] opening", row.doctype)
	personOpen.value = null
	// A check-in carries its photo and reason on the row; the request sheet
	// loads its own document.
	selected.value = { doctype: row.doctype, name: row.name, row }
}
function close() {
	selected.value = null
	// A decision made in the sheet changes the queue.
	waiting.reload()
}

// A request in the confirm sheet, named the way the list names it.
const byKey = computed(() => new Map(rows.value.map((row) => [rowKey(row), row])))
function rowLabel(req) {
	const row = byKey.value.get(rowKey(req))
	return row ? `${row.who} · ${[row.when, row.detail].filter(Boolean).join(" · ")}` : req.name
}

// How long a request has waited, in words and as a tone (amber from 7 days, red from 14).
const today = () => siteToday(new Date(), siteTimeZone())
const waited = (row) => daysWaiting(row.modified, today())
const tone = (row) => ageTone(waited(row))
const ageWords = (row) => {
	const days = waited(row)
	return days < 1 ? __("Today") : days === 1 ? __("1 day") : __("{0} days", [days])
}
const ageText = (row) => __("since {0}", [$dayjs(row.modified).format("D MMM")])

// Approve many: ask the server which would go through, show it, then approve those.
// The server adds no rule of its own: each request goes through the same decide() as one by one.
const sheet = ref(null) // null | { phase: "check" | "ready" | "working", ready: [], refused: [] }
const checkMany = createResource({ url: "hrms.api.approval.check_many" })
const decideMany = createResource({ url: "hrms.api.approval.decide_many" })

// closing the sheet while the server is approving would hide what it is doing
function dismissSheet() {
	if (sheet.value?.phase !== "working") sheet.value = null
}

async function startApprove() {
	if (overCap(ticked.value)) {
		return gToast({
			title: __("Approve up to 50 at a time"),
			text: __("Untick some and try again."),
			variant: "warning",
		})
	}
	sheet.value = { phase: "check", ready: [], refused: [] }
	try {
		const result = await checkMany.submit({ items: itemsFor(ticked.value, visibleRows.value) })
		sheet.value = { phase: "ready", ready: result.ready, refused: result.refused }
	} catch (error) {
		console.warn("[Approvals] the check failed", error)
		// stay in the sheet with a way to try again; the ticks are kept
		sheet.value = { phase: "failed", ready: [], refused: [], retry: startApprove }
	}
}

async function confirmApprove() {
	const current = sheet.value
	if (!current || current.phase !== "ready" || !current.ready.length) return
	sheet.value = { ...current, phase: "working" }
	try {
		// only the ones the check said would go through, with the revision the approver saw
		const result = await decideMany.submit({ items: current.ready })
		const done = afterApprove(ticked.value, result)
		ticked.value = done.selected
		sheet.value = null
		gToast({
			title: done.approved === 1 ? __("1 approved") : __("{0} approved", [done.approved]),
			text: done.refused.length ? __("{0} stayed in your list.", [done.refused.length]) : "",
			variant: done.refused.length ? "warning" : "success",
		})
		await waiting.reload()
	} catch (error) {
		console.warn("[Approvals] bulk approve failed", error)
		// what went through is unknown until the list is read again; say so, keep the ticks
		sheet.value = { phase: "failed", ready: [], refused: [], retry: startApprove }
		await waiting.reload()
	}
}

async function refresh(event) {
	console.info("[Approvals] pull-to-refresh")
	await waiting.reload()
	event.target?.complete?.()
}
</script>

<style scoped>
.g-approvals__dept {
	padding: 12px 16px 0;
	font-weight: 600;
}
.g-approvals__kind {
	padding: 8px 16px 0;
}
.g-approvals__chips {
	display: flex;
	gap: 8px;
	overflow-x: auto;
	scrollbar-width: none;
}
.g-approvals__chip,
.g-approvals__select,
.g-approvals__clear {
	min-height: var(--g-touch-target-min);
	padding: 0 12px;
	border: 1px solid var(--g-hair);
	border-radius: 999px;
	background: transparent;
	color: var(--g-ink);
	white-space: nowrap;
	cursor: pointer;
}
.g-approvals__chip--on {
	background: var(--g-ink);
	color: var(--g-bg);
}
.g-approvals__select,
.g-approvals__clear {
	border-color: transparent;
	color: var(--g-accent-ink);
}
.g-approvals__tick {
	display: grid;
	place-items: center;
	width: 22px;
	height: 22px;
	border: 2px solid var(--g-ink-3);
	border-radius: 999px;
}
.g-approvals__tick--on {
	background: var(--g-accent);
	border-color: var(--g-accent);
	color: var(--g-on-brand);
}
/* a number AND a word: colour is never the only signal (WCAG 1.4.1) */
.g-approvals__age {
	font-size: 12px;
	font-weight: 600;
	padding: 2px 8px;
	border-radius: 999px;
	white-space: nowrap;
}
.g-approvals__age--calm {
	color: var(--g-ink-2);
}
.g-approvals__age--amber {
	color: var(--g-warn-ink);
	background: rgb(var(--g-warn-ink-rgb) / 0.08);
}
.g-approvals__age--red {
	color: var(--g-danger-ink);
	background: rgb(var(--g-danger-ink-rgb) / 0.08);
}
.g-approvals__bar {
	position: sticky;
	bottom: 0;
	z-index: 3;
	display: flex;
	align-items: center;
	gap: 12px;
	padding: 12px 16px;
	border-top: 1px solid var(--g-hair);
	background: var(--g-sheet-bg);
}
.g-approvals__toggle {
	display: flex;
	width: 100%;
	align-items: center;
	justify-content: space-between;
	min-height: var(--g-touch-target-min);
	background: transparent;
	border: 0;
	padding: 0;
	cursor: pointer;
}
</style>
