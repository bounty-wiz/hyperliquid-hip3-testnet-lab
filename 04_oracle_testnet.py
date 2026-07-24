#!/usr/bin/env python3
"""Preview, and optionally publish, HIP-3 oracle updates on testnet."""

from __future__ import annotations

import argparse
import os
import sys
import time
from datetime import datetime, timezone
from typing import Any

from eth_account import Account
from hyperliquid.api import API
from hyperliquid.info import Info
from hyperliquid.utils.signing import get_timestamp_ms, sign_l1_action

from hip3_common import (
    TESTNET_API_URL,
    build_set_oracle_action,
    emit_json,
    validate_perp_price,
)


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(
        description=(
            "Build a testnet setOracle action. Nothing is submitted unless "
            "--execute is present and the confirmation succeeds."
        )
    )
    result.add_argument("--dex", required=True)
    result.add_argument("--symbol", required=True)
    result.add_argument("--oracle-px", required=True)
    result.add_argument("--mark-px")
    result.add_argument("--external-perp-px")
    result.add_argument("--sz-decimals", type=int, default=2)
    result.add_argument("--iterations", type=int, default=1)
    result.add_argument("--interval", type=float, default=3.0)
    result.add_argument("--execute", action="store_true")
    result.add_argument("--yes", action="store_true")
    result.add_argument("--output")
    return result


def submit(action: dict[str, Any], wallet: Any) -> Any:
    nonce = get_timestamp_ms()
    signature = sign_l1_action(wallet, action, None, nonce, None, False)
    return API(TESTNET_API_URL).post(
        "/exchange",
        {
            "action": action,
            "nonce": nonce,
            "signature": signature,
            "vaultAddress": None,
            "expiresAfter": None,
        },
    )


def main() -> int:
    args = parser().parse_args()
    if args.iterations < 1:
        print("ERROR: iterations must be positive", file=sys.stderr)
        return 2
    if args.iterations > 1 and args.interval < 3.0:
        print("ERROR: use at least 3 seconds between oracle updates", file=sys.stderr)
        return 3

    coin = f"{args.dex}:{args.symbol}"
    mark_px = args.mark_px or args.oracle_px
    external_px = args.external_perp_px or args.oracle_px
    for price in (args.oracle_px, mark_px, external_px):
        validate_perp_price(price, args.sz_decimals)

    action = build_set_oracle_action(
        dex=args.dex,
        oracle_pxs={coin: args.oracle_px},
        mark_pxs=[{coin: mark_px}],
        external_perp_pxs={coin: external_px},
    )
    preview = {
        "mode": "DRY_RUN",
        "network": "testnet",
        "iterations": args.iterations,
        "intervalSeconds": args.interval,
        "action": action,
        "submitted": False,
    }
    if not args.execute:
        emit_json(preview, args.output)
        return 0

    private_key = os.environ.get("HIP3_TESTNET_PRIVATE_KEY")
    if not private_key:
        print(
            "ERROR: --execute requires HIP3_TESTNET_PRIVATE_KEY. "
            "Never put it in code or commit it.",
            file=sys.stderr,
        )
        return 4
    wallet = Account.from_key(private_key)
    info = Info(TESTNET_API_URL, skip_ws=True)

    dex = next(
        (
            item
            for item in info.perp_dexs()
            if isinstance(item, dict) and item.get("name") == args.dex
        ),
        None,
    )
    if dex is None:
        print(
            f"ERROR: DEX '{args.dex}' was not returned by testnet perpDexs.",
            file=sys.stderr,
        )
        return 5

    universe = info.meta(dex=args.dex)["universe"]
    all_coins = [item["name"] for item in universe]
    if all_coins != [coin]:
        print(
            "ERROR: this classroom publisher supports only a single-asset DEX. "
            "externalPerpPxs must include every DEX asset; current assets are "
            f"{all_coins}.",
            file=sys.stderr,
        )
        return 6

    actual_sz_decimals = universe[0]["szDecimals"]
    if actual_sz_decimals != args.sz_decimals:
        print(
            f"ERROR: market {coin} has szDecimals={actual_sz_decimals}, but "
            f"the command used --sz-decimals={args.sz_decimals}.",
            file=sys.stderr,
        )
        return 7

    configured_updater = dex.get("oracleUpdater")
    allowed_updaters = {(configured_updater or dex["deployer"]).lower()}
    for variant, users in dex.get("subDeployers", []):
        if variant == "setOracle":
            allowed_updaters.update(user.lower() for user in users)
    if wallet.address.lower() not in allowed_updaters:
        print(
            f"ERROR: wallet {wallet.address} is not an authorized oracle "
            f"updater for DEX '{args.dex}'.",
            file=sys.stderr,
        )
        return 8

    expected = f"ORACLE {coin}"
    if not args.yes:
        typed = input(f"Type '{expected}' to publish on TESTNET: ")
        if typed != expected:
            print("Submission cancelled.", file=sys.stderr)
            return 9
    elif os.environ.get("HIP3_TESTNET_I_UNDERSTAND") != "YES":
        print(
            "ERROR: non-interactive execution also requires "
            "HIP3_TESTNET_I_UNDERSTAND=YES.",
            file=sys.stderr,
        )
        return 10

    results = []
    for index in range(args.iterations):
        results.append(
            {
                "iteration": index + 1,
                "submittedAtUtc": datetime.now(timezone.utc).isoformat(),
                "response": submit(action, wallet),
            }
        )
        if index + 1 < args.iterations:
            time.sleep(args.interval)

    emit_json(
        {
            **preview,
            "mode": "SUBMITTED",
            "wallet": wallet.address,
            "submitted": True,
            "results": results,
        },
        args.output,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

