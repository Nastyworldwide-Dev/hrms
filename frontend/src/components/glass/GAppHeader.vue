<!--
  GAppHeader — app header (spec §10.3 #24): title, notification bell with
  unread dot, avatar. Ports the behaviour of the existing BaseLayout.vue
  header, which is NOT modified (phase 4 swaps it in).

  DELIBERATELY NOT GLASS. §15.2's per-screen arithmetic counts no header
  ("calendar + 3 tiles + ghost + tabs = 6"), and a glass header alongside the
  glass tab bar would spend 2 of the 6-surface budget on chrome before any
  content exists. Flagged: the spec never states the header's material.

  BRAND (owner, 23 Sep): a tab page shows the Nadi mark at the left; a pushed
  page shows Back there instead. The date is content and lives in Home's
  Today card, not here. lg: the avatar link is hidden (the side nav carries
  identity, §20.2).

  Routing is emitted, not hardcoded, so phase 4's shell owns navigation:
  @notifications → the Notifications route, @profile → the Profile route.

  Props:
    title       string — falls back to "Nadi", as the existing header does
    unread      number, default 0 — >0 shows the unread dot
    avatarUrl   string — avatar image; falls back to the initial
    avatarLabel string — name behind the initial and the accessible name
  Slots:
    actions     optional — rendered in place of the bell and avatar
  Emits: notifications, profile, back
-->
<template>
	<!-- iOS navigation bar (alpha.7 §5.1): a tab root shows a LARGE title,
	     a pushed screen Back + a centred inline title + its own actions. -->
	<header
		class="g-header"
		:class="{
			'g-header--large': !showBack,
			'g-header--inline': showBack,
			'g-header--collapsed': collapsed,
		}"
	>
		<!-- Back is GPage's decision, not this component's and not the screen's
		     (§12, v1.11): a pushed screen gets one, a tab root does not. -->
		<GIconButton
			v-if="showBack"
			:label="__('Back')"
			flush
			class="g-header__back"
			@click="$emit('back', $event)"
		>
			<svg class="g-icon" width="16" height="16" viewBox="0 0 16 16" aria-hidden="true">
				<polyline points="10 3 5 8 10 13" />
			</svg>
		</GIconButton>

		<!-- Decorative: the h1 beside it names the page (visually hidden on Home),
		     so a labelled mark would say "Nadi" twice to a screen reader. -->
		<GLogo v-if="!showBack" label="" />
		<!-- The small title that replaces the large one after it scrolls away. -->
		<span v-if="!showBack && title" class="g-header__mini" aria-hidden="true">{{ title }}</span>
		<!-- On a tab root the LARGE title is drawn by the page (BaseLayout) so it
		     scrolls with it; this h1 still names the page, visually hidden. -->
		<h1 class="g-header__title" :class="{ 'sr-only': !title || !showBack }">{{ title || __("Nadi") }}</h1>
		<!-- A hidden title takes no space, so this holds the bell and avatar at
		     the right edge on Home (the mark alone, 23 Sep). -->
		<span v-if="!title" class="g-header__spacer" aria-hidden="true" />

		<!-- A pushed screen's own controls (Refresh, Edit, a status, Filter)
		     take the place of the bell and avatar: one right-hand cluster, never
		     two. Absent the slot, the bell and avatar render exactly as before. -->
		<div v-if="$slots.actions" class="g-header__actions">
			<slot name="actions" />
		</div>
		<!-- Bell and avatar belong to the tab roots (B24); a pushed screen
		     keeps a spacer so its title stays centred. -->
		<span v-else-if="showBack" class="g-header__trail" aria-hidden="true" />
		<template v-else-if="!showBack">
		<button
			type="button"
			class="g-header__action g-focusable"
			:class="{ 'g-header__action--bounce': bouncing }"
			:aria-label="unread > 0 ? `Notifications, ${unread} unread` : 'Notifications'"
			@click="$emit('notifications', $event)"
		>
			<svg class="g-icon" width="16" height="16" viewBox="0 0 16 16" aria-hidden="true">
				<path d="M8 2a4 4 0 0 0-4 4v3l-1 2h10l-1-2V6a4 4 0 0 0-4-4Z" />
				<path d="M6.5 13a1.6 1.6 0 0 0 3 0" />
			</svg>
			<span v-if="unread > 0" class="g-header__dot" aria-hidden="true" />
		</button>

		<button
			type="button"
			class="g-header__avatar-link g-focusable"
			:aria-label="avatarLabel ? `Profile, ${avatarLabel}` : 'Profile'"
			@click="$emit('profile', $event)"
		>
			<!-- decorative: the button above already carries "Profile, <name>" -->
			<!-- 44 pt, the size of every bar button beside it (owner, 25 Sep 2026:
			     "bell icon is way bigger than profile"). -->
			<GAvatar :image="avatarUrl" :label="avatarLabel" :size="44" round decorative />
		</button>
		</template>
	</header>
</template>

<script setup>
import { inject, onBeforeUnmount, ref, watch } from "vue"
import GIconButton from "./GIconButton.vue"
import GAvatar from "./GAvatar.vue"
import GLogo from "./GLogo.vue"

const __ = inject("$translate")
// provided by GPage; false on tab roots
const showBack = inject("gShowBack", false)
//: BaseLayout's scroll says when the large title has gone (alpha.7 §5.1).
const collapsed = inject("gTitleCollapsed", false)

const props = defineProps({
	title: { type: String, default: "" },
	unread: { type: Number, default: 0 },
	avatarUrl: { type: String, default: "" },
	avatarLabel: { type: String, default: "" },
})
defineEmits(["notifications", "profile", "back"])

//: One bounce when something new arrives (Apple: Bounce, "an action
//: occurred"): the count ROSE. Not on first load (prev unknown), not when
//: reading notifications lowers it.
const BOUNCE_MS = 450
const bouncing = ref(false)
let bounceTimer = null
watch(
	() => props.unread,
	(next, prev) => {
		if (!(next > (prev ?? next))) return
		console.info("[GAppHeader] new notification; bell bounces once")
		bouncing.value = false
		clearTimeout(bounceTimer)
		requestAnimationFrame(() => {
			bouncing.value = true
			bounceTimer = setTimeout(() => (bouncing.value = false), BOUNCE_MS)
		})
	}
)
onBeforeUnmount(() => clearTimeout(bounceTimer))
</script>

<!-- No scoped style for theme-owned classes (8.16). A scoped rule carries a
     [data-v-*] attribute, so it outranks the theme layer — including its
     media queries — and the lint gate cannot see it because it only reads
     theme/glass-components.css. These declarations now live there. -->
