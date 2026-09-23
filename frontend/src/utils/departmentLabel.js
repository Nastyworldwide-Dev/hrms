// A department as people say it. ERPNext names each Department record
// "<name> - <company abbr>", and that record name reached the screen as
// "Production - NW0A". Keep the record name as the VALUE everywhere (filters,
// links); show this. Only the last " - X" is dropped, where X has no spaces,
// which is the shape ERPNext writes.
export function departmentLabel(name) {
	return String(name || "").replace(/ - [^\s]+$/, "")
}
