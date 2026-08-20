<!--
  GProviderButton — sign in with an external identity provider.

  PROVIDER-AGNOSTIC BY DESIGN. The server decides which providers exist
  (`hrms.api.oauth.oauth_providers`), and this component styles whatever it
  returns: the name and the mark both come from the provider record. Nothing
  here mentions any one vendor, so a provider enabled later inherits the
  treatment for free.

  THE MARK IS RENDERED UNMODIFIED. No filter, no grayscale, no recolour, no
  mask, no border-radius on the image, no forced monochrome. Identity providers
  publish brand guidelines that require their mark be used as supplied, and a
  design system that tints third-party logos to match itself is exactly the
  thing those guidelines forbid. If a mark clashes with the surface, that is a
  reason to change the surface.

  NOT a glass surface, deliberately. This button lives on the auth screens,
  which carry :field="false" (phase 4.2) because they render before a session
  and have no light field. §3 opens with the reason: "Glass requires colour
  behind it or it renders as grey fog." A translucent button over a flat
  background is exactly that fog, so this takes the §6.1 solid fill with the
  ghost action's metrics — pad-action, radius-action, --ink label.

  Props:
    name     string, required — the provider's display name, from the server
    icon     string — URL of the provider's mark, rendered as supplied
    href     string, required — the provider's auth URL
    label    string — full label override; defaults to "Sign in with {name}"
-->
<template>
	<a class="g-provider" :href="href">
		<img v-if="icon" class="g-provider__mark" :src="icon" alt="" aria-hidden="true" />
		<span>{{ label || `Sign in with ${name}` }}</span>
	</a>
</template>

<script setup>
defineProps({
	name: { type: String, required: true },
	icon: { type: String, default: "" },
	href: { type: String, required: true },
	label: { type: String, default: "" },
})
</script>
