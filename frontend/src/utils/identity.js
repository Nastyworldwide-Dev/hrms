// The comparable form of a login identity — the frontend twin of the backend
// hrms.utils.identity.normalize_login (strip + lowercase).
//
// The router guard in main.js compares the resolved employee's `user_id`
// against the session user's `name` to confirm the (shared-key) cached employee
// belongs to this user. A mirror-provisioned `user_id` can carry drifted case:
// it is written through `db.set_value`, which skips the lowercasing that
// `User.autoname` applies. The backend resolves such a user fine (it normalizes
// with Lower(Trim)), and then returns the raw stored `user_id` — so a raw `!==`
// in the guard bounces exactly the people the backend identity module exists to
// rescue straight to /invalid-employee. Normalize both sides, same rule as the
// server.
export function normalizeLogin(value) {
	return typeof value === "string" ? value.trim().toLowerCase() : ""
}
