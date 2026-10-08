#!/usr/bin/env python3
"""Offline, focused consistency check for the decoded SDK fixture contract (#562).

This checks deterministic fixture state transitions, not Soroban execution.
It needs only Python's standard library. Run:
    python scripts/verify_vault_fixtures.py
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

FIXTURE = Path(__file__).resolve().parents[1] / "fixtures/vault/decoded-scenarios.json"
INTEGER = re.compile(r"-?(?:0|[1-9][0-9]*)\Z")
CONTRACT_ERRORS = {
    1001: "AmountNotPositive",
    1005: "AmountBelowMinimumDeposit",
    4001: "InsufficientBalance",
    5003: "LockNotMatured",
}


def unique_pairs(pairs: list[tuple[str, object]]) -> dict:
    result: dict = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate fixture key: {key}")
        result[key] = value
    return result


def amount(value: object) -> int:
    if not isinstance(value, str) or INTEGER.fullmatch(value) is None:
        raise ValueError(f"amount/timestamp must be canonical decimal text: {value!r}")
    return int(value)


def check_state(state: dict) -> None:
    for key in ("available", "locked", "wallet", "vault_custody"):
        if amount(state[key]) < 0:
            raise ValueError(f"negative fixture state: {key}")
    live = [lock for lock in state["locks"] if not lock["withdrawn"]]
    if sum(amount(lock["amount"]) for lock in live) != amount(state["locked"]):
        raise ValueError("locked balance must equal live lock principal")
    if amount(state["vault_custody"]) != amount(state["available"]) + amount(state["locked"]):
        raise ValueError("single-actor vault custody must cover available + locked")
    for lock in state["locks"]:
        for key in ("id", "amount", "created_time", "unlock_time"):
            amount(lock[key])
        if lock["withdrawn"] and amount(lock["amount"]) != 0:
            raise ValueError("withdrawn lock must have zero remaining principal")


def main() -> int:
    doc = json.loads(FIXTURE.read_text(encoding="utf-8"), object_pairs_hook=unique_pairs)
    if doc["schema_version"] != 1 or not re.fullmatch("[0-9a-f]{40}", doc["source_main_sha"]):
        raise ValueError("unexpected schema or source SHA")
    seen: set[str] = set()
    states: dict[str, dict] = {}
    for scenario in doc["scenarios"]:
        key = scenario["id"]
        if key in seen:
            raise ValueError(f"duplicate scenario: {key}")
        seen.add(key)
        before, after = scenario["before"], scenario["after"]
        check_state(before)
        check_state(after)
        if amount(before["wallet"]) + amount(before["vault_custody"]) != amount(after["wallet"]) + amount(after["vault_custody"]):
            raise ValueError(f"token conservation failure: {key}")
        invoke = scenario["invoke"]
        method, args = invoke["method"], invoke["args"]
        timestamp = amount(scenario["at"])
        for arg in args[1:]:
            amount(arg)
        events = scenario["vault_events"]
        if not scenario["result"]["ok"]:
            if before != after or events:
                raise ValueError(f"rejected operation changed state or emitted vault event: {key}")
            error = scenario["result"]["error"]
            if error["domain"] == "contract":
                if CONTRACT_ERRORS.get(error["code"]) != error["name"]:
                    raise ValueError(f"unknown/misnamed contract error: {key}")
            elif error["domain"] == "host":
                if error["code"] is not None:
                    raise ValueError("host failure cannot invent a stable contract code")
            else:
                raise ValueError("unknown error domain")
        else:
            if len(events) != 1 or events[0]["topics"] != [method.replace("_funds", ""), args[0]]:
                # The exported ABI calls lock_funds; the emitted symbol is lock.
                raise ValueError(f"incorrect contract event topic: {key}")
            ev = events[0]["data"]
            for item in ev:
                amount(item)
            a0, l0, w0, c0 = (amount(before[k]) for k in ("available", "locked", "wallet", "vault_custody"))
            a1, l1, w1, c1 = (amount(after[k]) for k in ("available", "locked", "wallet", "vault_custody"))
            if method == "deposit":
                v = amount(args[1])
                expected = (a0 + v, l0, w0 - v, c0 + v, [str(v), str(a1)])
            elif method == "withdraw":
                v = amount(args[1])
                expected = (a0 - v, l0, w0 + v, c0 - v, [str(v), str(a1)])
            elif method == "lock_funds":
                v = amount(args[1])
                expected = (a0 - v, l0 + v, w0, c0, [str(v), args[2], str(a1), str(l1)])
            elif method == "withdraw_lock":
                matches = [lock for lock in before["locks"] if lock["id"] == args[1] and not lock["withdrawn"]]
                if len(matches) != 1 or timestamp < amount(matches[0]["unlock_time"]):
                    raise ValueError(f"successful claim missing matured lock: {key}")
                v = amount(matches[0]["amount"])
                expected = (a0, l0 - v, w0 + v, c0 - v, [args[1], str(v)])
            else:
                raise ValueError(f"unsupported success method: {method}")
            if (a1, l1, w1, c1, ev) != expected:
                raise ValueError(f"unexpected state delta or event payload: {key}")
        states[key] = after

    for read in doc["reads"]:
        state = states[read["from"]]
        e = read["expected"]
        if e["get_balance"] != state["available"] or e["get_locked_balance"] != state["locked"]:
            raise ValueError(f"read vs state mismatch: {read['id']}")
        can_withdraw = any(
            not lock["withdrawn"] and amount(read["at"]) >= amount(lock["unlock_time"])
            for lock in state["locks"]
        )
        if e["can_withdraw"] is not can_withdraw:
            raise ValueError(f"maturity mismatch: {read['id']}")
        if "get_lock" in e and e["get_lock"] != state["locks"][0]:
            raise ValueError(f"lock read mismatch: {read['id']}")
    print(f"Fixture consistency PASS: {len(seen)} scenarios; {len(doc['reads'])} reads")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (ValueError, KeyError, IndexError, json.JSONDecodeError) as exc:
        print(f"FIXTURE_HOLD: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc
