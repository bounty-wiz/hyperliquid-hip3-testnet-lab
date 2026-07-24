from __future__ import annotations

import unittest

from hip3_common import (
    build_register_asset2_action,
    build_set_oracle_action,
    hype_to_native_units,
    validate_perp_price,
)

UPDATER = "0x1111111111111111111111111111111111111111"


class ActionBuilderTests(unittest.TestCase):
    def test_hype_conversion(self) -> None:
        self.assertEqual(hype_to_native_units("500"), 50_000_000_000)
        self.assertEqual(hype_to_native_units("0.00000001"), 1)

    def test_register_asset2_shape(self) -> None:
        action = build_register_asset2_action(
            dex="demo",
            coin="demo:ASSET",
            full_name="Demo",
            collateral_token=0,
            oracle_updater=UPDATER,
            max_gas_native_units=50_000_000_000,
            sz_decimals=2,
            oracle_px="100.0",
            margin_table_id=10,
            margin_mode="strictIsolated",
        )
        self.assertIn("registerAsset2", action)
        self.assertNotIn("registerAsset", action)
        self.assertEqual(
            action["registerAsset2"]["assetRequest"]["coin"],
            "demo:ASSET",
        )
        self.assertEqual(
            action["registerAsset2"]["schema"]["collateralToken"],
            0,
        )

    def test_zero_max_gas_is_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "reserve deployment"):
            build_register_asset2_action(
                dex="demo",
                coin="demo:ASSET",
                full_name="Demo",
                collateral_token=0,
                oracle_updater=UPDATER,
                max_gas_native_units=0,
                sz_decimals=2,
                oracle_px="100.0",
                margin_table_id=10,
                margin_mode="strictIsolated",
            )

    def test_oracle_tuple_arrays_are_sorted(self) -> None:
        action = build_set_oracle_action(
            dex="demo",
            oracle_pxs={"demo:B": "2", "demo:A": "1"},
            mark_pxs=[{"demo:B": "2", "demo:A": "1"}],
            external_perp_pxs={"demo:B": "2", "demo:A": "1"},
        )
        self.assertEqual(
            action["setOracle"]["oraclePxs"],
            [("demo:A", "1"), ("demo:B", "2")],
        )
        self.assertEqual(
            action["setOracle"]["markPxs"][0],
            [("demo:A", "1"), ("demo:B", "2")],
        )

    def test_oracle_requires_complete_external_prices(self) -> None:
        with self.assertRaisesRegex(ValueError, "exactly"):
            build_set_oracle_action(
                dex="demo",
                oracle_pxs={"demo:A": "1", "demo:B": "2"},
                mark_pxs=[],
                external_perp_pxs={"demo:A": "1"},
            )

    def test_rejects_unnamespaced_coin(self) -> None:
        with self.assertRaisesRegex(ValueError, "namespaced"):
            build_register_asset2_action(
                dex="demo",
                coin="ASSET",
                full_name="Demo",
                collateral_token=0,
                oracle_updater=UPDATER,
                max_gas_native_units=50_000_000_000,
                sz_decimals=2,
                oracle_px="100.0",
                margin_table_id=10,
                margin_mode="strictIsolated",
            )

    def test_rejects_invalid_new_dex_length(self) -> None:
        with self.assertRaisesRegex(ValueError, "2 to 4"):
            build_register_asset2_action(
                dex="builderdex",
                coin="builderdex:ASSET",
                full_name="Demo",
                collateral_token=0,
                oracle_updater=UPDATER,
                max_gas_native_units=50_000_000_000,
                sz_decimals=2,
                oracle_px="100.0",
                margin_table_id=10,
                margin_mode="strictIsolated",
            )

    def test_perpetual_price_precision(self) -> None:
        validate_perp_price("100.12", 2)
        validate_perp_price("123456", 6)
        with self.assertRaisesRegex(ValueError, "significant figures"):
            validate_perp_price("100.123", 2)
        with self.assertRaisesRegex(ValueError, "decimal places"):
            validate_perp_price("0.00001", 2)


if __name__ == "__main__":
    unittest.main()

