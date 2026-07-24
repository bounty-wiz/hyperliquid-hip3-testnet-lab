#!/usr/bin/env python3
"""Preflight, and optionally submit, registerAsset2 on testnet."""

from __future__ import annotations

import argparse
import os
import sys
from decimal import Decimal
from typing import Any

from eth_account import Account
from hyperliquid.api import API
from hyperliquid.info import Info
from hyperliquid.utils.signing import get_timestamp_ms, sign_l1_action

from hip3_common import (
    TESTNET_API_URL,
    build_register_asset2_action,
    emit_json,
    hype_to_native_units,
    validate_address,
)


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(
        description=(
            "Run live testnet preflight checks. Nothing is submitted unless "
            "--execute is present and the confirmation succeeds."
        )
    )
    result.add_argument("--dex", required=True)
    result.add_argument("--symbol", required=True)
    result.add_argument("--full-name", required=True)
    result.add_argument("--oracle-px", required=True)
    result.add_argument("--max-gas-hype", required=True)
    result.add_argument("--collateral-token", type=int, default=0)
    result.add_argument("--updater-address")
    result.add_argument("--sz-decimals", type=int, default=2)
    result.add_argument("--margin-table-id", type=int, default=10)
    result.add_argument(
        "--margin-mode",
        choices=("strictIsolated", "noCross", "normal"),
        default="strictIsolated",
    )
    result.add_argument("--execute", action="store_true")
    result.add_argument("--yes", action="store_true")
    result.add_argument("--output")
    return result


def submit(action: dict[str, Any], wallet: Any) -> Any:
    nonce = get_timestamp_ms()
    signature = sign_l1_action(
        wallet,
        action,
        None,
        nonce,
        None,
        False,
    )
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
    wallet = None

    if args.execute:
        private_key = os.environ.get("HIP3_TESTNET_PRIVATE_KEY")
        if not private_key:
            print(
                "ERROR: --execute requires HIP3_TESTNET_PRIVATE_KEY. "
                "Never put it in code or commit it.",
                file=sys.stderr,
            )
            return 2
        wallet = Account.from_key(private_key)

    updater_address = (
        args.updater_address
        or os.environ.get("HIP3_TESTNET_ADDRESS")
        or (wallet.address if wallet is not None else None)
    )
    if updater_address is None:
        print(
            "ERROR: provide --updater-address or set HIP3_TESTNET_ADDRESS. "
            "A dry-run does not need a private key.",
            file=sys.stderr,
        )
        return 3
    validate_address(updater_address)

    coin = f"{args.dex}:{args.symbol}"
    max_gas_native_units = hype_to_native_units(args.max_gas_hype)
    action = build_register_asset2_action(
        dex=args.dex,
        coin=coin,
        full_name=args.full_name,
        collateral_token=args.collateral_token,
        oracle_updater=updater_address,
        max_gas_native_units=max_gas_native_units,
        sz_decimals=args.sz_decimals,
        oracle_px=args.oracle_px,
        margin_table_id=args.margin_table_id,
        margin_mode=args.margin_mode,
    )

    info = Info(TESTNET_API_URL, skip_ws=True)
    if any(
        isinstance(item, dict) and item.get("name") == args.dex
        for item in info.perp_dexs()
    ):
        print(
            f"ERROR: DEX '{args.dex}' already exists on testnet. "
            "Choose a fresh 2-to-4-character name.",
            file=sys.stderr,
        )
        return 4

    collateral = next(
        (
            token
            for token in info.spot_meta()["tokens"]
            if token["index"] == args.collateral_token
        ),
        None,
    )
    if collateral is None:
        print(
            f"ERROR: collateral token index {args.collateral_token} was not "
            "returned by testnet spotMeta.",
            file=sys.stderr,
        )
        return 5

    auction = info.query_perp_deploy_auction_status()
    current_auction_price_hype = Decimal(auction["currentGas"])
    if current_auction_price_hype > Decimal(args.max_gas_hype):
        print(
            f"ERROR: current auction price {current_auction_price_hype} HYPE "
            f"exceeds the configured {args.max_gas_hype} HYPE cap.",
            file=sys.stderr,
        )
        return 6

    preview = {
        "mode": "READY_TO_SIGN" if args.execute else "LIVE_DRY_RUN",
        "network": "testnet",
        "signer": wallet.address if wallet is not None else None,
        "oracleUpdater": updater_address.lower(),
        "auction": auction,
        "collateral": {
            "index": collateral["index"],
            "name": collateral["name"],
            "tokenId": collateral["tokenId"],
            "role": "trader margin and settlement asset; not a liquidity pool",
        },
        "action": action,
        "submitted": False,
    }

    if not args.execute:
        emit_json(preview, args.output)
        return 0

    expected = f"DEPLOY {coin}"
    if not args.yes:
        typed = input(f"Type '{expected}' to submit this TESTNET action: ")
        if typed != expected:
            print("Submission cancelled.", file=sys.stderr)
            return 7
    elif os.environ.get("HIP3_TESTNET_I_UNDERSTAND") != "YES":
        print(
            "ERROR: non-interactive execution also requires "
            "HIP3_TESTNET_I_UNDERSTAND=YES.",
            file=sys.stderr,
        )
        return 8

    response = submit(action, wallet)
    emit_json(
        {
            **preview,
            "mode": "SUBMITTED",
            "submitted": True,
            "response": response,
        },
        args.output,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

