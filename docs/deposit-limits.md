# Vault Deposit Limits

The Savings Vault supports global minimum and maximum bounds on each deposit call.

## Configuration

- `min_deposit_amount`: rejects a positive deposit below the configured value.
- `max_deposit_amount`: rejects a deposit above the configured value.
- `0` disables the corresponding bound.
- When both values are enabled, the minimum must not exceed the maximum.

Both setters require current-admin authorization. Deposit validation runs before
the Stellar Asset Contract transfer.

Read the values with `get_min_deposit_amount()`,
`get_max_deposit_amount()`, or `get_config()`.

## Boundary examples

| Minimum | Maximum | Deposit | Result |
|---:|---:|---:|---|
| 0 | 0 | any positive amount | allowed |
| 100 | 0 | 99 | rejected |
| 100 | 0 | 100 | allowed |
| 0 | 1,000 | 1,000 | allowed |
| 0 | 1,000 | 1,001 | rejected |
| 100 | 1,000 | 100 through 1,000 | allowed |

Changing a bound affects later deposits only; existing balances and locks are
not rewritten.

## Per-user cap strategy

This change does not treat `Balance(user)` as a cumulative user cap because
that value contains only unlocked balance. Moving principal into a lock or
withdrawing it changes the available balance, so it is not a durable measure
of outstanding principal.

A future outstanding-principal cap should use dedicated persistent accounting,
for example `UserPrincipal(Address)`: increment after a successful deposit,
decrement after successful unlocked or matured-lock withdrawal, leave it
unchanged when principal moves between unlocked and locked states, and check
the value plus the next deposit before transfer. Existing deployments would
need an explicit migration that reconstructs principal from unlocked balance
plus non-withdrawn locks.

That storage and migration work is intentionally separate from this per-call
limit feature.

## Errors

- `AmountBelowMinimumDeposit (1005)`
- `MinDepositAmountNegative (1007)`
- `AmountAboveMaximumDeposit (1008)`
- `MaxDepositAmountNegative (1009)`
- `DepositLimitRangeInvalid (1010)`

See [error-codes.md](error-codes.md) for canonical meanings.

## Admin boundary

The admin may configure future deposit sizes but these settings do not change
existing user balances, locks, or withdrawal rules. Restrictive values can
prevent new deposits, so clients should display the configured bounds before
a user prepares a deposit.
