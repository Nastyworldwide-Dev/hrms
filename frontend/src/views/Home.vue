<template>
	<BaseLayout :pageTitle="__('Today')">
		<template #body>
			<!-- §20.3: ONE content column, 720px, left-aligned against the side nav.
			     Until the 7.3 ruling this split into lg:grid-cols-2 — measured 550px
			     and 549px, neither of them 720 — with the request panel behind a
			     border-l. Nothing in §20 authorised a screen splitting in two at
			     desktop, and the divergence was invisible below lg:, which is how
			     three build batches passed over it. Same correction on Leave and
			     Attendance. -->
			<!-- Pull to refresh: the socket is not a delivery guarantee on a phone,
			     so the employee always has a hand-driven way to see the decided
			     status without a full reload (A-C1). -->
			<!-- gap-5, not gap-8. The fold is a BUDGET, not a length:
			     USABLE = 100dvh - header - tab bar (64 + 9 + safe-area) -
			     padding, which is ~440px at 360x640 and ~640px at 390x844.
			     Four panels at gap-8 spent 96px of that on air alone, on a
			     screen measured at 1382px of content for ten tap targets.
			     Sized against the SMALLEST budget, every larger phone gains
			     list rows instead of needing its own layout. Invariant F1 and
			     the arithmetic: src/views/__tests__/home-fold-budget.test.js. -->
			<GPullRefresh @refresh="refresh" />
			<div
				class="g-rows--compact flex flex-col gap-5 px-4 pt-6 pb-8 w-full max-w-content-column-lg mx-auto lg:py-7"
			>
				<!-- alpha.7 Home (plan §3, §10.3; owner + senior, 25 Sep).
				     1. Announcements FIRST, the same place every day, never gone:
				        the senior's goal is that people read them. A quiet day
				        is one line. Must-read notices open full screen (§4.4).
				     2. The Today card directly under it, still on the first
				        screen: the status and the one button on ONE solid card
				        (Wallet / Fitness style; glass stays on controls).
				     3. Needs you (approvers), 4. Your week. -->
				<!-- iPhone Safari only, once per 30 days (alpha.7 0.10). -->
				<InstallHint />
				<Announcements />
				<section class="g-today" :aria-label="__('Check in')">
					<NowBar />
					<CheckInPanel />
				</section>
				<NeedsYou />
				<div class="w-full">
					<div class="g-eyebrow mb-4">{{ __("Your week") }}</div>
					<GListPanel
						:loading="!homeWeek.data && !homeComingUp.data && homeWeek.loading"
						:rows="2"
					>
						<HomeWeek />
						<HomeComingUp />
					</GListPanel>
				</div>
			</div>
		</template>
	</BaseLayout>
</template>

<script setup>
import { homeAnnouncements } from "@/data/announcements"
import { homeComingUp, homeWeek } from "@/data/home"
import { needsYouResource } from "@/data/needsYou"
import { nowResource } from "@/data/now"
import { pendingCountResource } from "@/data/remoteCheckin"

import CheckInPanel from "@/components/CheckInPanel.vue"
import NowBar from "@/components/NowBar.vue"
import InstallHint from "@/components/InstallHint.vue"
import NeedsYou from "@/components/NeedsYou.vue"
import Announcements from "@/components/Announcements.vue"
import HomeWeek from "@/components/HomeWeek.vue"
import GListPanel from "@/components/glass/GListPanel.vue"
import HomeComingUp from "@/components/HomeComingUp.vue"
import BaseLayout from "@/components/BaseLayout.vue"
import GPullRefresh from "@/components/glass/GPullRefresh.vue"

//: The date is the header title, said once and in plain case (approved Home
//: plan, H2/H3): "Wed 23 Sep". A fixed length, so it never crowds the bell.

//: Pull to refresh reloads what HOME shows. It reloaded the request lists,
//: which left Home with the Requests panel (review of 1cdd9ff56).
async function refresh(event) {
	console.info("[Home] pull-to-refresh")
	await Promise.allSettled([
		nowResource.reload(),
		needsYouResource.reload(),
		// NeedsYou's remote check-in row reads its own count (data/remoteCheckin).
		pendingCountResource.reload(),
		homeAnnouncements.reload(),
		homeWeek.reload(),
		homeComingUp.reload(),
	])
	event.target?.complete?.()
}
</script>
