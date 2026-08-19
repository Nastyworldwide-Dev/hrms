// MUST be main.js's FIRST import — this is load-bearing, not style.
//
// frappe-ui fires `auto: true` resources SYNCHRONOUSLY inside createResource
// (resources.js: `if (options.auto) out.fetch()`), and a resource declared at
// module scope therefore fetches while the import graph is still evaluating —
// BEFORE any code in main.js's body has run. Its fetch resolves
// `options.resourceFetcher || getConfig('resourceFetcher') || request`, and
// with the config not yet set it falls back to the BARE `request`, which
// never prefixes `/api/method/` and defaults to GET.
//
// That is exactly what took the Team feature down in production on
// 2026-08-19: SideNav (entry chunk) imports data/team.js, whose three
// auto resources fired first and hit
//   GET https://<site>/hrms.api.team.has_team  ->  404 (an HTML page)
// so has_team / is_approver / get_managers failed for every fresh session
// and the Team page + Team tabs vanished — while anyone with an old
// localStorage cache kept a stale `true` and saw no problem.
//
// Evaluating the config in a module imported FIRST closes the race for every
// module-scope resource, present and future. ES module evaluation order is
// depth-first in source order, so this module completes before App.vue's
// import graph ever evaluates.
//
// Wrapped, never raw: this is the one seam every resource in the app passes
// through, so it is the only place a failure can be reported once instead of
// in seventeen templates. See utils/loudRequest.js for why that matters.
import { setConfig, frappeRequest } from "frappe-ui"
import { makeLoudRequest } from "@/utils/loudRequest"

setConfig("resourceFetcher", makeLoudRequest(frappeRequest))
