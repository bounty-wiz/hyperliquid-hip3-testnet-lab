#!/usr/bin/env python3
"""Build HIP-3 action envelopes without network access or a wallet."""

from __future__ import annotations

import argparse

from hip3_common import (
    build_register_asset2_action,
    build_set_oracle_action,
    emit_json,
    hype_to_native_units,
)

DEMO_UPDATER = "0x1111111111111111111111111111111111111111"


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(
        description="Build unsigned registerAsset2 and setOracle actions."
    )
    result.add_argument("--dex", default="demo")
    result.add_argument("--symbol", default="ASSET")
    result.add_argument("--full-name", default="Classroom Demo DEX")
    result.add_argument("--updater-address", default=DEMO_UPDATER)
    result.add_argument("--max-gas-hype", default="500")
    result.add_argument("--oracle-px", default="100.0")
    result.add_argument("--output")
    return result


def main() -> int:
    args = parser().parse_args()
    coin = f"{args.dex}:{args.symbol}"
    max_gas_native_units = hype_to_native_units(args.max_gas_hype)

    register_action = build_register_asset2_action(
        dex=args.dex,
        coin=coin,
        full_name=args.full_name,
        collateral_token=0,
        oracle_updater=args.updater_address,
        max_gas_native_units=max_gas_native_units,
        sz_decimals=2,
        oracle_px=args.oracle_px,
        margin_table_id=10,
        margin_mode="strictIsolated",
    )
    oracle_action = build_set_oracle_action(
        dex=args.dex,
        oracle_pxs={coin: args.oracle_px},
        mark_pxs=[{coin: args.oracle_px}],
        external_perp_pxs={coin: args.oracle_px},
    )

    emit_json(
        {
            "mode": "OFFLINE_DRY_RUN",
            "submitted": False,
            "maxGas": {
                "hype": args.max_gas_hype,
                "nativeUnits": max_gas_native_units,
            },
            "registerAction": register_action,
            "firstOracleAction": oracle_action,
            "safety": {
                "networkCalled": False,
                "walletLoaded": False,
                "actionSigned": False,
                "transactionSubmitted": False,
            },
        },
        args.output,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

