// The comparison a list filter uses (alpha.7 0.6). The Filters sheet no
// longer asks for "=", ">" or "<": a "From" date keeps days on or after it,
// a "To" date keeps days on or before it, anything else matches exactly.
const FROM = new Set(["from_date", "start_date"])
const TO = new Set(["to_date", "end_date"])

export function filterCondition({ fieldname, fieldtype }) {
	if (fieldtype === "Date" && FROM.has(fieldname)) return ">="
	if (fieldtype === "Date" && TO.has(fieldname)) return "<="
	return "="
}
