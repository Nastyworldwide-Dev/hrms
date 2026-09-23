<!--
  ShellHeader — GAppHeader wired to the app: unread count, the signed-in
  user's avatar, and the three routes it emits (alpha.5, one shell).

  Screens that own their own ion-content (lists, forms, Notifications, You)
  could not use BaseLayout, so each drew its own <header> with a 2px hairline
  and no bell or avatar — the "old Frappe" look. They use this instead; so does
  BaseLayout, so there is one wiring.

  Props:
    title  string — the screen's name (GAppHeader shows the Nadi mark if empty)
    bare   boolean — no ion-header wrapper, for a screen that lays itself out
           inside its own ion-content (FormView, SopDetail)
    back   function — replaces the default Back (goBackOrHome), for a screen
           that must confirm before leaving (a dirty form)
  Slots:
    actions — passed through to GAppHeader, in place of bell and avatar
-->
<template>
	<component
		:is="bare ? 'div' : IonHeader"
		:class="bare ? 'flex-none g-page__content' : 'ion-no-border g-page__content'"
	>
		<div class="w-full max-w-md mx-auto lg:max-w-none lg:mx-0">
			<GAppHeader
				:title="title"
				:unread="unreadNotificationsCount.data || 0"
				:avatar-url="user?.data?.user_image"
				:avatar-label="user?.data?.first_name"
				@notifications="router.push({ name: 'Notifications' })"
				@profile="router.push({ name: 'Profile' })"
				@back="onBack"
			>
				<template v-if="$slots.actions" #actions>
					<slot name="actions" />
				</template>
			</GAppHeader>
		</div>
	</component>
</template>

<script setup>
import { inject } from "vue"
import { useRouter } from "vue-router"
import { IonHeader } from "@ionic/vue"

import GAppHeader from "@/components/glass/GAppHeader.vue"
import { unreadNotificationsCount } from "@/data/notifications"
import { goBackOrHome } from "@/utils/navigation"

const props = defineProps({
	title: { type: String, default: "" },
	bare: { type: Boolean, default: false },
	back: { type: Function, default: null },
})

const router = useRouter()
const user = inject("$user", null)

function onBack() {
	if (props.back) return props.back()
	goBackOrHome(router)
}
</script>
