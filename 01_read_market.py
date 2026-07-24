#!/usr/bin/env python3
"""Read a live HIP-3 market without loading a wallet."""

from __future__ import annotations

import argparse
import sys
from datetime import datetime, timezone
from importlib.metadata import version
from pathlib import Path
from typing import Any

from hyperliquid.info import Info

from hip3_common import NETWORK_URLS, emit_json


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(
        description="Read a HIP-3 DEX and market without a wallet."
    )
    result.add_argument("--network", choices=NETWORK_URLS, default="testnet")
    result.add_argument("--dex", default="test")
    result.add_argument("--coin", default="test:ABC")
    result.add_argument("--output")
    return result


def summarize_dex(item: dict[str, Any]) -> dict[str, Any]:
    return {
        key: item.get(key)
        for key in ("name", "fullName", "deployer", "oracleUpdater", "feeRecipient")
    }


def fail(message: str, code: int, output: str | None) -> int:
    rendered = f"ERROR: {message}"
    print(rendered, file=sys.stderr)
    if output:
        path = Path(output)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(rendered + "\n", encoding="utf-8")
    return code


def main() -> int:
    args = parser().parse_args()
    api_url = NETWORK_URLS[args.network]
    info = Info(api_url, skip_ws=True)

    dex_index_and_item = next(
        (
            (index, item)
            for index, item in enumerate(info.perp_dexs())
            if isinstance(item, dict) and item.get("name") == args.dex
        ),
        None,
    )
    if dex_index_and_item is None:
        return fail(
            f"DEX '{args.dex}' was not returned by perpDexs on {args.network}",
            2,
            args.output,
        )

    dex_index, dex = dex_index_and_item
    metadata, contexts = info.post(
        "/info",
        {"type": "metaAndAssetCtxs", "dex": args.dex},
    )
    universe = metadata["universe"]
    market_index = next(
        (
            index
            for index, market in enumerate(universe)
            if market["name"] == args.coin
        ),
        None,
    )
    if market_index is None:
        return fail(
            f"coin '{args.coin}' was not returned by meta for DEX '{args.dex}'",
            3,
            args.output,
        )

    limits = info.post("/info", {"type": "perpDexLimits", "dex": args.dex})
    coin_oi_caps = dict(limits.get("coinToOiCap", []))

    result = {
        "mode": "READ_ONLY",
        "network": args.network,
        "apiUrl": api_url,
        "observedAtUtc": datetime.now(timezone.utc).isoformat(),
        "sdkVersion": version("hyperliquid-python-sdk"),
        "auction": info.query_perp_deploy_auction_status(),
        "dex": {"index": dex_index, **summarize_dex(dex)},
        "market": {
            "indexInMeta": market_index,
            "actionAssetId": 100_000 + dex_index * 10_000 + market_index,
            "metadata": universe[market_index],
            "context": contexts[market_index],
            "annotation": info.post(
                "/info",
                {"type": "perpAnnotation", "coin": args.coin},
            ),
        },
        "limits": {
            "coinOiCap": coin_oi_caps.get(args.coin),
            "totalOiCap": limits.get("totalOiCap"),
            "sizeCapPerPerp": limits.get("oiSzCapPerPerp"),
        },
        "status": info.post(
            "/info",
            {"type": "perpDexStatus", "dex": args.dex},
        ),
        "safety": {
            "walletLoaded": False,
            "actionSigned": False,
            "transactionSubmitted": False,
        },
    }
    emit_json(result, args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

