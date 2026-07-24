"""Shared action builders and validation for the HIP-3 testnet lab."""

from __future__ import annotations

import json
import re
from decimal import Decimal
from pathlib import Path
from typing import Any

HYPE_NATIVE_UNITS = Decimal("100000000")
TESTNET_API_URL = "https://api.hyperliquid-testnet.xyz"
MAINNET_API_URL = "https://api.hyperliquid.xyz"
NETWORK_URLS = {
    "testnet": TESTNET_API_URL,
    "mainnet": MAINNET_API_URL,
}
ADDRESS_RE = re.compile(r"^0x[0-9a-fA-F]{40}$")


def hype_to_native_units(value: str) -> int:
    """Convert a decimal HYPE amount to HyperCore native-token units."""
    amount = Decimal(value)
    if amount < 0:
        raise ValueError("HYPE amount cannot be negative")
    native_units = amount * HYPE_NATIVE_UNITS
    if native_units != native_units.to_integral_value():
        raise ValueError("HYPE supports at most 8 decimal places")
    return int(native_units)


def validate_new_dex_name(dex: str) -> None:
    """Validate the current registerAsset2 DEX-name constraint."""
    if not 2 <= len(dex) <= 4:
        raise ValueError("new DEX names must contain 2 to 4 characters")
    if ":" in dex:
        raise ValueError("DEX name cannot contain ':'")


def validate_namespaced_coin(dex: str, coin: str) -> None:
    """Require the builder-perp {dex}:{symbol} wire name."""
    if not coin.startswith(f"{dex}:") or coin.count(":") != 1:
        raise ValueError(f"coin must use the namespaced form '{dex}:SYMBOL'")
    symbol = coin.split(":", 1)[1]
    if not symbol:
        raise ValueError("coin symbol cannot be empty")


def validate_address(address: str) -> None:
    if not ADDRESS_RE.fullmatch(address):
        raise ValueError("address must be a 42-character hexadecimal EVM address")


def validate_perp_price(value: str, sz_decimals: int) -> None:
    """Apply the documented perpetual price-precision rule."""
    price = Decimal(value)
    if price <= 0:
        raise ValueError("perpetual price must be positive")

    normalized = price.normalize()
    if normalized == normalized.to_integral_value():
        return

    decimal_places = max(-normalized.as_tuple().exponent, 0)
    if decimal_places > 6 - sz_decimals:
        raise ValueError(
            "perpetual price has too many decimal places for szDecimals"
        )
    if len(normalized.as_tuple().digits) > 5:
        raise ValueError(
            "non-integer perpetual prices can have at most 5 significant figures"
        )


def build_register_asset2_action(
    *,
    dex: str,
    coin: str,
    full_name: str,
    collateral_token: int,
    oracle_updater: str,
    max_gas_native_units: int,
    sz_decimals: int,
    oracle_px: str,
    margin_table_id: int,
    margin_mode: str,
) -> dict[str, Any]:
    """Build the current registerAsset2 action without signing it."""
    validate_new_dex_name(dex)
    validate_namespaced_coin(dex, coin)
    validate_address(oracle_updater)

    if margin_mode not in {"strictIsolated", "noCross", "normal"}:
        raise ValueError("invalid margin mode")
    if max_gas_native_units <= 0:
        raise ValueError(
            "maxGas must be positive; zero consumes a reserve deployment"
        )
    if not 0 <= sz_decimals <= 6:
        raise ValueError("this lab requires szDecimals between 0 and 6")
    if collateral_token < 0:
        raise ValueError("collateral token index cannot be negative")
    if margin_table_id <= 0:
        raise ValueError("marginTableId must be positive")

    validate_perp_price(oracle_px, sz_decimals)

    return {
        "type": "perpDeploy",
        "registerAsset2": {
            "maxGas": max_gas_native_units,
            "assetRequest": {
                "coin": coin,
                "szDecimals": sz_decimals,
                "oraclePx": oracle_px,
                "marginTableId": margin_table_id,
                "marginMode": margin_mode,
            },
            "dex": dex,
            "schema": {
                "fullName": full_name,
                "collateralToken": collateral_token,
                "oracleUpdater": oracle_updater.lower(),
            },
        },
    }


def build_set_oracle_action(
    *,
    dex: str,
    oracle_pxs: dict[str, str],
    mark_pxs: list[dict[str, str]],
    external_perp_pxs: dict[str, str],
) -> dict[str, Any]:
    """Build a deterministically sorted setOracle action."""
    expected_coins = set(oracle_pxs)
    if not expected_coins:
        raise ValueError("at least one oracle price is required")
    if set(external_perp_pxs) != expected_coins:
        raise ValueError("externalPerpPxs must contain exactly the oracle coins")
    if len(mark_pxs) > 2:
        raise ValueError("markPxs can contain zero, one, or two maps")

    for prices in [oracle_pxs, external_perp_pxs, *mark_pxs]:
        for coin, price in prices.items():
            validate_namespaced_coin(dex, coin)
            if Decimal(price) <= 0:
                raise ValueError(f"price for {coin} must be positive")

    return {
        "type": "perpDeploy",
        "setOracle": {
            "dex": dex,
            "oraclePxs": sorted(oracle_pxs.items()),
            "markPxs": [sorted(prices.items()) for prices in mark_pxs],
            "externalPerpPxs": sorted(external_perp_pxs.items()),
        },
    }


def emit_json(value: Any, output: str | None = None) -> None:
    rendered = json.dumps(value, indent=2)
    print(rendered)
    if output:
        path = Path(output)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(rendered + "\n", encoding="utf-8")

