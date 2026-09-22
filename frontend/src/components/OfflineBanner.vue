<!--
  OfflineBanner — the app says it has lost the network (pre-2.0 R3).

  Nothing told the employee before this. A phone that loses signal mid-shift
  behaved exactly like a slow server: the tap did nothing, a spinner sat there,
  and they pressed again. The checklist asks that "no records" and "failed to
  load" be distinguishable; "the phone is not connected" is that same rule one
  layer further down, and it is the one the employee can actually act on.

  NOT GBanner, though the specimen draws this case with one. GBanner is a
  glass surface (§15.1) and this renders in App.vue, above every screen — so
  it would add a compositing layer to all forty-odd of them, on a budget of
  six, and the surfaces gate would never see it because that gate walks
  views/ only. A screen that silently costs one more than it is charged for is
  exactly what §15.3 exists to prevent. An opaque bar costs nothing and reads
  the same.

  It is also NOT dismissible. A banner you can close is a banner that is wrong
  the moment it is closed — the condition it reports has not changed. It goes
  away when the network comes back, and only then.
-->
<template>
	<Transition name="g-offline">
		<div v-if="!online" class="g-offline" role="status">
			<span class="g-offline__dot" aria-hidden="true" />
			{{ __("No connection. Anything you send now will not reach us.") }}
		</div>
	</Transition>
</template>

<script setup>
import { inject } from "vue"

import { useOnline } from "@/composables/useOnline"

const __ = inject("$translate")
const online = useOnline()
</script>
