CLASS: money printed by hand as "{CODE} {amount}" instead of through the
app formatter (symbol). Live audit 23 Sep: "INR 50.00" on Requests while other
screens print the symbol.

Call sites (grep for `${currency} ${` in frontend/src): RequestBalances money() — same-root, fixed (formatCurrency). No other.
Note: fresh.local test company is INR; the live company is MYR, which prints "RM".
