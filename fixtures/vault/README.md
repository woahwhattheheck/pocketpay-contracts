# SDK integration fixtures — Savings Vault

This package gives SDK and mobile teams deterministic **decoded** contract
examples without a wallet, network, private key, live testnet, RPC quota,
deployment or generated Rust client. It covers #562 (deposit, withdrawal,
locks, read models, contract/host failures, and structured event tuples).

## Files

- [`decoded-scenarios.json`](decoded-scenarios.json) — nine independent
  transaction scenarios and four read-model expectations.
- [`scripts/verify_vault_fixtures.py`](../../scripts/verify_vault_fixtures.py)
  — one standard-library-only offline fixture consistency check.

The fixture data corresponds to the Savings Vault implementation at sponsor
main commit `7988c6efec9a73162ed7d2fffb3b8b6ebd5a7b67`. When the ABI changes,
update these examples from the **actual contract implementation** and rerun
the focused check.

## Format and types

`scenarios[*]` provides `invoke`, `at`, `before`, `after`, `result`,
and `vault_events`. Successful entries include one Savings Vault event,
with `topics: [eventSymbol, subject]` and `data: [positional values]`.
Failure entries explicitly preserve the before/after state and emit no vault
event. `reads[*]` proves read-only `get_balance`, `get_locked_balance`,
`get_lock`, and `can_withdraw` expectations for those states.

All `i128`, `u64`, timestamp and lock-id values are **decimal strings**.
Parse them with `BigInt(text)` or arbitrary-precision integer libraries, not
floating-point `Number()`. Only stable contract error `u32` codes are JSON
integers. `fixture-alice` is a synthetic **actor label**, deliberately not
a Stellar StrKey or a signing secret; map it to a generated test address
before invoking a real Soroban contract.

These are **post-decoding value fixtures**, NOT serialized ScVal/XDR,
`simulateTransaction` responses, real transaction receipts or proofs that
Soroban code has been executed. They omit the Stellar Asset Contract's own
`transfer` event, which occurs before a successful Vault `deposit` or
`withdraw` event. Only Vault events appear here.

### Critical event ABI distinction

The actual `withdraw` implementation emits **two** payload values:
`(amount, new_available_balance)`. It does not withdraw matured locks,
does not emit a `new_locked` field and does not change locked principal.
Consumers must call `withdraw_lock` on individual matured lock IDs;
its payload is `(lock_id, amount)`. `lock_funds` emits four values:
`(amount, unlock_time, new_available_balance, active_unmatured_locked)`.
The [event-schema reference](../../docs/event-schema.md) is reconciled to
the contract's actual emitted tuples in this contribution.

## Example TypeScript consumer assertions

```ts
import fixtures from "./fixtures/vault/decoded-scenarios.json";
const deposit = fixtures.scenarios.find(s => s.id === "deposit-success")!;
const [kind, actor] = deposit.vault_events[0].topics;
const [amount, balance] = deposit.vault_events[0].data.map(BigInt);
if (kind !== "deposit" || actor !== "fixture-alice") throw Error("topic drift");
if (amount !== 500n || balance !== 500n) throw Error("decoded ABI drift");

const withdrawn = fixtures.scenarios.find(s => s.id === "withdraw-available-success")!;
if (withdrawn.vault_events[0].data.length !== 2) throw Error("wrong withdraw tuple");
```

## Focused consistency check

```bash
python scripts/verify_vault_fixtures.py
```

It verifies fixture schema version, duplicate keys/IDs, integer encoding,
balance and SAC token conservation, before/after deltas for each supported
operation, correct event tuples, failed-operation rollback, maturity boundaries,
and read-result consistency. This is **fixture consistency validation**, not a
Soroban integration test; real contract execution, gas profiles, authorization
signatures, and RPC decoding require their own focused follow-up if the
sponsor asks for those acceptance checks.

Fixture scenarios contain no wallet secrets or live identities.
