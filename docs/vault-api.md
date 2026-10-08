# Savings Vault Public API — Legacy Page

> **Superseded.** This page previously described a draft contract interface
> that does not match the deployed `SavingsVault` source. Do not use the old
> signatures, type names, or version promises for new integrations.

For the current API, see the [Savings Vault Public API Reference and
Compatibility Policy](vault-public-api.md), which is pinned to
`contracts/savings_vault/src/lib.rs` at
`7988c6efec9a73162ed7d2fffb3b8b6ebd5a7b67`.

The authoritative contract is
[`contracts/savings_vault/src/lib.rs`](../contracts/savings_vault/src/lib.rs).
It exposes `ContractError`, `LockEntry`, `initialize(admin, token)`,
`lock_funds(user, amount, unlock_time)`, `transfer_admin(admin, new_admin)`,
and other documented entrypoints. The former examples of `VaultError`,
`LockData`, `create_lock`, `transfer_ownership`, and an unconditional
`v1.0.0` stability promise were **not** an accurate public ABI.

For SDK/mobile compatibility decisions, use the canonical reference's
public types, events, numeric error codes, authorization contract, storage
implications, and breaking-change review checklist. Future changes to the
canonical reference must accompany the source change; this legacy filename is
kept only to redirect existing links.
