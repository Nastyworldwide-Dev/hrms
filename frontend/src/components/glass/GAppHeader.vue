<!--
  GAppHeader — app header (spec §10.3 #24): title, notification bell with
  unread dot, avatar. Ports the behaviour of the existing BaseLayout.vue
  header, which is NOT modified (phase 4 swaps it in).

  DELIBERATELY NOT GLASS. §15.2's per-screen arithmetic counts no header
  ("calendar + 3 tiles + ghost + tabs = 6"), and a glass header alongside the
  glass tab bar would spend 2 of the 6-surface budget on chrome before any
  content exists. Flagged: the spec never states the header's material.

  lg: BEHAVIOUR — preserved from the existing header, which differs at lg::
  the avatar link is hidden (the side nav carries identity, §20.2) and a date
  kicker appears. NOTE: §20.7 does not list #24 among the components that
  differ at lg:. That list is incomplete — flagged for a spec amendment rather
  than resolved here.

  Routing is emitted, not hardcoded, so phase 4's shell owns navigation:
  @notifications → the Notifications route, @profile → the Profile route.

  Props:
    title       string — falls back to "Frappe HR", as the existing header does
    unread      number, default 0 — >0 shows the unread dot
    kicker      string — lg:-only date kicker, e.g. "WEDNESDAY, 20 AUGUST"
    avatarUrl   string — avatar image; falls back to the initial
    avatarLabel string — name behind the initial and the accessible name
  Emits: notifications, profile
-->
<template>
	<header class="g-header">
		<h1 class="g-header__title">{{ title || __("Frappe HR") }}</h1>

		<span v-if="kicker" class="g-header__kicker">{{ kicker }}</span>

		<button
			type="button"
			class="g-header__action g-focusable"
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
			<img v-if="avatarUrl" class="g-header__avatar" :src="avatarUrl" alt="" />
			<span v-else class="g-header__avatar" aria-hidden="true">{{ initial }}</span>
		</button>
	</header>
</template>

<script setup>
import { inject } from "vue"

const __ = inject("$translate")
import { computed } from "vue"

const props = defineProps({
	title: { type: String, default: "" },
	unread: { type: Number, default: 0 },
	kicker: { type: String, default: "" },
	avatarUrl: { type: String, default: "" },
	avatarLabel: { type: String, default: "" },
})
defineEmits(["notifications", "profile"])

const initial = computed(() => (props.avatarLabel || "?").charAt(0).toUpperCase())
</script>

<!-- No scoped style for theme-owned classes (8.16). A scoped rule carries a
     [data-v-*] attribute, so it outranks the theme layer — including its
     media queries — and the lint gate cannot see it because it only reads
     theme/glass-components.css. These declarations now live there. -->
