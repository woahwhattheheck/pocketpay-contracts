# Savings Vault Public API Reference & Compatibility Policy

This is the public integration reference for the PocketPay Savings Vault contract at source commit `7988c6efec9a73162ed7d2fffb3b8b6ebd5a7b67` and contract version `0.1.0`.

The authoritative implementation is [`contracts/savings_vault/src/lib.rs`](../contracts/savings_vault/src/lib.rs). If this document and the contract disagree, the contract is authoritative and this reference should be updated in the same change that modifies the public surface.

## Compatibility contract

### Stable public surface

SDK and mobile consumers may treat these as compatibility-sensitive:

- public function names, argument order/types, and return types;
- public `#[contracttype]` field names and field types;
- numeric `ContractError` codes;
- authorization requirements;
- event topic names/positions and payload tuple shapes;
- the semantic split between unlocked balance and per-lock funds;
- per-user, monotonically increasing lock IDs.

### Experimental and operational surface

These may evolve without an ABI break, but still require documentation and behavior review:

- configured minimum-deposit and lock-duration values;
- operator-selected pause duration;
- pagination request sizes and the current `MAX_LOCK_PAGE_SIZE = 50` cap;
- read-helper implementation strategy and resource cost;
- diagnostic log wording;
- off-chain indexing recommendations;
- internal storage/migration implementation that preserves externally observable state.

### Breaking changes

A change is breaking when it removes/renames an entrypoint, changes an argument or return shape, renumbers/reuses an error code, changes an event topic/payload schema, changes required authorization, or changes persisted-state semantics so existing state cannot be interpreted safely by current clients.

A breaking change requires:

1. a version/migration note describing old and new behavior;
2. an explicit compatibility-impact section in the PR;
3. SDK and mobile call-site review before merge;
4. event/error decoder review when those schemas change;
5. storage migration or new-deployment guidance when persisted state changes;
6. focused contract tests for the changed behavior.

Do not silently reuse an old error code or event topic for new semantics.

## Public contract types

### `LockEntry`

| Field | Type | Meaning |
|---|---|---|
| `id` | `u64` | Per-user lock identifier, starting at 1. |
| `owner` | `Address` | Lock owner. |
| `amount` | `i128` | Locked token amount; set to 0 after withdrawal. |
| `created_time` | `u64` | Ledger timestamp when created. |
| `unlock_time` | `u64` | Earliest withdrawal timestamp. |
| `withdrawn` | `bool` | True after successful lock withdrawal. |

### `BalanceSnapshot`

| Field | Type | Meaning |
|---|---|---|
| `unlocked` | `i128` | Deposited balance available to `withdraw`. |
| `locked` | `i128` | Sum of all non-withdrawn locks. |
| `total` | `i128` | `unlocked + locked`. |
| `withdrawable` | `i128` | Sum of matured, non-withdrawn locks. |

### `LockSummary`

| Field | Type | Meaning |
|---|---|---|
| `active_count` | `u32` | Non-withdrawn lock count. |
| `total_locked_amount` | `i128` | Sum of non-withdrawn lock amounts. |
| `matured_count` | `u32` | Matured, non-withdrawn lock count. |
| `withdrawable_amount` | `i128` | Sum of matured, non-withdrawn amounts. |
| `earliest_unlock` | `u64` | Earliest immature unlock time, or 0. |
| `latest_unlock` | `u64` | Latest immature unlock time, or 0. |

### `ContractConfig`

| Field | Type | Meaning |
|---|---|---|
| `token` | `Address` | Accepted Stellar Asset Contract address. |
| `admin` | `Address` | Current vault admin. |
| `version` | `String` | Contract version; currently `0.1.0`. |
| `paused` | `bool` | Effective pause state; expired pauses report false. |
| `pause_expiry` | `u64` | Stored pause-expiry timestamp, or 0. |
| `min_deposit_amount` | `i128` | Deposit floor, or 0 when disabled. |
| `max_lock_duration` | `u64` | Maximum new-lock duration, or 0 when disabled. |
| `min_lock_duration` | `u64` | Minimum new-lock duration, or 0 when disabled. |

## Public entrypoints

The implicit Soroban `Env` argument is omitted below.

| Function | Arguments | Return | Authorization | State / behavior |
|---|---|---|---|---|
| `initialize` | `admin: Address, token: Address` | `()` | admin signs | One-time setup; stores admin/token/version and emits `initialize`. |
| `get_version` | — | `String` | none | Returns `0.1.0`; validates/migrates storage when initialized. |
| `get_token` | — | `Address` | none | Returns configured SAC token. |
| `pause` | `admin: Address, duration_secs: u64` | `()` | stored admin signs | Sets bounded emergency pause and expiry. |
| `unpause` | `admin: Address` | `()` | stored admin signs | Clears pause and expiry. |
| `set_min_deposit_amount` | `admin: Address, min_amount: i128` | `()` | stored admin signs | Sets deposit floor; 0 disables it. |
| `get_min_deposit_amount` | — | `i128` | none | Returns floor; 0 when absent. |
| `set_max_lock_duration` | `admin: Address, max_duration_secs: u64` | `()` | stored admin signs | Sets maximum duration for new locks; 0 disables it. |
| `get_max_lock_duration` | — | `u64` | none | Returns maximum; 0 when absent. |
| `set_min_lock_duration` | `admin: Address, min_duration_secs: u64` | `()` | stored admin signs | Sets minimum duration for new locks; 0 disables it. |
| `get_min_lock_duration` | — | `u64` | none | Returns minimum; 0 when absent. |
| `is_paused` | — | `bool` | none | Returns effective pause state. |
| `get_config` | — | `ContractConfig` | none | Returns current public configuration. |
| `deposit` | `user: Address, amount: i128` | `()` | user signs | Transfers SAC user → vault and credits unlocked balance; pause-gated. |
| `withdraw` | `user: Address, amount: i128` | `()` | user signs | Transfers unlocked balance vault → user; not pause-gated. |
| `withdraw_lock` | `user: Address, lock_id: u64` | `()` | user signs | Withdraws one matured lock; marks it withdrawn and zeroes amount. |
| `get_balance` | `user: Address` | `i128` | none | Returns unlocked deposited balance only. |
| `get_balance_snapshot` | `user: Address` | `BalanceSnapshot` | none | Aggregates unlocked/locked/total/withdrawable amounts. |
| `get_lock_summary` | `user: Address` | `LockSummary` | none | Aggregates lock counts, amounts, and unlock window. |
| `lock_funds` | `user: Address, amount: i128, unlock_time: u64` | `u64` | user signs | Creates an independent lock ID; pause-gated. |
| `extend_lock` | `user: Address, lock_id: u64, new_unlock_time: u64` | `()` | user signs | Moves an active lock later; currently pause-gated. |
| `get_locked_balance` | `user: Address` | `i128` | none | Sum of all non-withdrawn locks. |
| `can_withdraw` | `user: Address` | `bool` | none | True if at least one non-withdrawn lock is mature. |
| `get_lock` | `user: Address, lock_id: u64` | `Option<LockEntry>` | none | Returns one lock or `None`. |
| `list_locks` | `user: Address, offset: u32, limit: u32` | `Vec<LockEntry>` | none | Oldest-first page; limit capped at 50. |
| `list_matured_locks` | `user: Address, offset: u32, limit: u32` | `Vec<LockEntry>` | none | Matured/non-withdrawn page; limit capped at 50. |
| `get_matured_lock_count` | `user: Address` | `u32` | none | Counts matured, non-withdrawn locks. |
| `get_matured_balance` | `user: Address` | `i128` | none | Sums matured, non-withdrawn lock amounts. |
| `get_admin` | — | `Address` | none | Returns current admin. |
| `transfer_admin` | `admin: Address, new_admin: Address` | `()` | stored admin signs | Replaces admin; rejects self/contract-address targets. |

### Behavior notes

- `deposit`, `withdraw`, and `withdraw_lock` move the configured SAC token.
- `withdraw` affects only unlocked `Balance(user)`; each matured lock is withdrawn separately by ID.
- `lock_funds` creates independent per-user locks and never overwrites an earlier lock.
- `extend_lock` enforces a future time strictly later than the existing lock, but does not reapply the configured min/max new-lock duration checks.
- Snapshot/summary/matured-lock helpers scan historical lock IDs; resource cost grows with lock history.
- The min-deposit/min-lock/max-lock getters return 0 when unset and do not themselves require initialization; most other vault reads do.
- `require_auth()` failures are Soroban host authorization failures, not numbered `ContractError` variants.

## Contract errors

Numeric codes are integration identifiers.

| Code | Variant | Meaning |
|---:|---|---|
| 1001 | `AmountNotPositive` | Non-positive deposit, withdrawal, or lock amount. |
| 1002 | `UnlockTimeNotInFuture` | New lock/extension time is not after ledger time. |
| 1003 | `LockDurationExceedsMaximum` | New lock exceeds configured max duration. |
| 1004 | `LockDurationBelowMinimum` | New lock is shorter than configured min duration. |
| 1005 | `AmountBelowMinimumDeposit` | Deposit is below configured floor. |
| 1006 | `PauseDurationMustBePositive` | Pause duration is zero. |
| 1007 | `MinDepositAmountNegative` | Negative deposit floor. |
| 2001 | `NotAuthorizedAdmin` | Supplied admin differs from stored admin. |
| 3001 | `AlreadyInitialized` | Repeated initialization. |
| 3002 | `NotInitialized` | Operation requires initialization. |
| 3003 | `ContractPaused` | Pause-gated action attempted during active pause. |
| 4001 | `InsufficientBalance` | Withdrawal exceeds unlocked balance. |
| 4002 | `InsufficientBalanceToLock` | Lock amount exceeds unlocked balance. |
| 5001 | `LockNotFound` | Referenced lock ID does not exist. |
| 5002 | `LockAlreadyWithdrawn` | Withdraw/extend attempted after lock withdrawal. |
| 5003 | `LockNotMatured` | Lock withdrawal attempted before maturity. |
| 5004 | `ExtendLockTimeNotIncreased` | Extension does not move the lock later. |
| 6001 | `StorageVersionUnsupported` | Stored version is incompatible with this WASM. |
| 6002 | `RequiredStorageEntryMissing` | Required instance state is absent. |
| 7001 | `TokenNotConfigured` | SAC token address is unavailable. |
| 8001 | `CannotTransferAdminToSelf` | Admin rotation targets current admin. |
| 8002 | `CannotTransferAdminToContractAddress` | Admin rotation targets the vault contract. |

SAC token-contract failures may also surface from `deposit`, `withdraw`, or `withdraw_lock`; those are not remapped into the vault error enum.

## Events

Topic and payload shapes are compatibility-sensitive.

| Operation | Topics | Data payload |
|---|---|---|
| initialize | `("initialize", admin)` | `token: Address` |
| pause | `("pause", admin)` | `expiry: u64` |
| unpause | `("unpause", admin)` | `()` |
| set_min_deposit_amount | `("cfg_min", admin)` | `min_amount: i128` |
| set_max_lock_duration | `("cfg_maxlk", admin)` | `max_duration_secs: u64` |
| set_min_lock_duration | `("cfg_minlk", admin)` | `min_duration_secs: u64` |
| deposit | `("deposit", user)` | `(amount: i128, new_balance: i128)` |
| withdraw | `("withdraw", user)` | `(amount: i128, new_balance: i128)` |
| withdraw_lock | `("withdraw_lock", user)` | `(lock_id: u64, withdrawn_amount: i128)` |
| lock_funds | `("lock", user)` | `(amount: i128, unlock_time: u64, available_balance: i128, active_immature_locked: i128)` |
| extend_lock | `("extend_lock", user)` | `(lock_id: u64, old_unlock_time: u64, new_unlock_time: u64, amount: i128)` |
| transfer_admin | `("xferadmin", old_admin)` | `new_admin: Address` |

Rust diagnostic logs are not part of the event compatibility contract.

## Storage implications

Clients should not read raw storage as an API. This inventory exists so reviewers can identify migration-sensitive changes.

**Instance storage:** `Admin`, `Initialized`, `Token`, `StorageVersion`, `Paused`, `PauseExpiry`, `MinDepositAmount`, `MaxLockDurationSecs`, `MinLockDurationSecs`.

**Persistent storage:** `Balance(Address)`, `Lock(Address, u64)`, and `NextLockId(Address)`. `Locks(Address)` remains declared for legacy/helper compatibility but is not the primary current lock-write path.

Current v0→v1 migration only writes the storage-version marker because the layouts are otherwise compatible. A stored version different from the compiled `STORAGE_VERSION = 1` is rejected rather than guessed at.

A storage representation change is breaking unless migration preserves balances, lock ownership/maturity/withdrawal state, admin/token configuration, and public event/error semantics.

## Review checklist

For changes to the vault public surface, verify:

- public function names, arguments, returns, and authorization;
- public struct field names/types;
- numeric error codes and meanings;
- event topics and payload shapes;
- pause and withdrawal behavior;
- storage layout and migration;
- SDK/mobile generated-client and decoder impact;
- this reference is updated in the same PR;
- breaking changes include version/migration guidance.

Related documents:

- [Authorisation rules](authorisation-rules.md)
- [Failure mode catalogue](failure-mode-catalogue.md)
- [Storage migration](storage-migration.md)
- [Multi-lock storage](multi-lock-storage.md)
- [Read models](read-models.md)
- [SDK error mapping guide](sdk-error-mapping-guide.md)
