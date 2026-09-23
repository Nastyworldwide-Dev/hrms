<template>
	<BaseLayout>
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
				class="flex flex-col gap-5 px-4 pt-6 pb-8 w-full max-w-content-column-lg mx-auto lg:p-7"
			>
				<!-- §3.1's order, and the order is the argument: what is
				     happening now, what is waiting on you, what you already
				     asked for. The quick links that used to sit in the middle
				     answered "how do I start a request?" — a question the
				     Requests tab now answers in one tap from anywhere, which
				     is why Home's largest block could go. -->
				<!-- FIRST, above the check-in button: what is true right now,
				     so the button underneath is a decision rather than a guess
				     (§2). Renders nothing when there is no shift and no open
				     session, which is most of a day off. -->
				<NowBar />
				<CheckInPanel />
				<!-- Owner-approved Home (23 Sep 2026): News sits right under
				     Today "so everyone will notice… kinda like news". Every block
				     below ALWAYS renders and says why it is empty. -->
				<Announcements />
				<!-- ONE panel for the two one-line blocks (§15.2, surfaces gate:
				     Home was 8/6). Each keeps its own title and empty line. -->
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
				<NeedsYou />
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
