// "3 days", "1 day" — never "day(s)" (audit P2-3). English only needs one or
// many; pass the plural when it is not the singular plus "s". Kept free of Vue
// imports so node tests can load it.
export function countOf(n, one, many = `${one}s`) {
	return `${n} ${Number(n) === 1 ? one : many}`
}
