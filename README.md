# Hyperliquid HIP-3 testnet lab

Runnable companion code for learning the HIP-3 deployment lifecycle on
Hyperliquid testnet.

The lab separates four boundaries that should not be blurred:

1. Read a live market without a wallet.
2. Build the current wire actions offline.
3. Run live preflight checks before optionally signing a testnet deployment.
4. Preview an oracle update before optionally publishing it on testnet.

Every command is read-only or a dry-run by default. State-changing commands
require `--execute`, a disposable testnet private key, and an explicit
confirmation.

> [!WARNING]
> This is educational software, not audited deployment or oracle
> infrastructure. HIP-3 rules and live network state can change. Recheck the
> official documentation immediately before signing anything.

## What this deploys

HIP-3 registers a perpetual DEX and a perpetual market. It does **not** mint a
spot token or ERC-20.

For the classroom example:

- `demo` is the DEX namespace.
- `demo:ASSET` is a perpetual contract, not a token.
- `collateralToken: 0` currently selects USDC on testnet.
- Collateral is the asset traders use for margin and settlement. It is not an
  AMM liquidity pool.

## Requirements

- Python 3.10 or newer
- Internet access for the live read and preflight exercises
- A disposable funded testnet wallet only if you choose to execute a
  state-changing exercise

This repository pins the official Python SDK version used for verification:

```text
hyperliquid-python-sdk==0.24.0
```

## Setup

```bash
git clone https://github.com/bounty-wiz/hyperliquid-hip3-testnet-lab.git
cd hyperliquid-hip3-testnet-lab

python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

Windows PowerShell activation:

```powershell
.venv\Scripts\Activate.ps1
```

Do not configure a private key yet. The first three dry-runs do not need one.

## 1. Read a live HIP-3 market

```bash
python 01_read_market.py \
  --network testnet \
  --dex test \
  --coin test:ABC
```

This reads public HyperCore state and prints:

- the deployment auction;
- the DEX namespace and operator addresses;
- market metadata and live context;
- the derived order-action asset ID;
- open-interest limits and DEX status.

It loads no wallet, signs no action, and submits no transaction.

The official testnet example `test:ABC` currently derives asset ID `110000`:

```text
100000 + dexIndex(1) × 10000 + marketIndex(0) = 110000
```

Live prices, limits, indexes, and market availability are observations rather
than constants.

## 2. Build the actions offline

```bash
python 02_preview_actions.py \
  --dex demo \
  --symbol ASSET
```

This builds and prints unsigned `registerAsset2` and `setOracle` actions. It
does not call the network or load a wallet.

The example uses:

- a 500 HYPE `maxGas` cap for demonstration only;
- USDC token index `0` as example collateral;
- `marginTableId=10`, `szDecimals=2`, and `strictIsolated` as classroom inputs,
  not risk recommendations;
- a dummy oracle-updater address that must never be used for a real
  deployment.

The action builder rejects `maxGas=0` because the current action reference says
zero consumes a reserve deployment at the current auction price.

## 3. Run a live deployment preflight

Choose a fresh two-to-four-character DEX name. Provide only the public address
that would operate the oracle:

```bash
export HIP3_TESTNET_ADDRESS='0xYOUR_PUBLIC_ADDRESS'

python 03_deploy_testnet.py \
  --dex zqjx \
  --symbol DEMO \
  --full-name "Classroom Demo DEX" \
  --oracle-px 100.0 \
  --max-gas-hype 500
```

The default mode is still a dry-run. It:

- confirms the DEX name is not already registered;
- reads the current deployment auction;
- aborts if the current auction price exceeds your cap;
- resolves the chosen collateral token from live `spotMeta`;
- prints the unsigned action with `"submitted": false`.

The dry-run does not read `HIP3_TESTNET_PRIVATE_KEY`.

Replace the example 500 HYPE cap with a cap you deliberately choose after
reading the current auction. A maximum is not a recommendation.

### Optional: submit on testnet

Only continue with a disposable testnet-only wallet that has the required
testnet assets and permissions. The official faucet documentation describes
mock USDC but does not document a complete path for obtaining the testnet HYPE
required by the deployment auction. If you cannot fund the auction safely, stop
at the authentic dry-run.

Export the private key only in the current shell:

```bash
export HIP3_TESTNET_PRIVATE_KEY='0x...'
```

Then repeat the same command with `--execute`:

```bash
python 03_deploy_testnet.py \
  --dex zqjx \
  --symbol DEMO \
  --full-name "Classroom Demo DEX" \
  --oracle-px 100.0 \
  --max-gas-hype 500 \
  --execute
```

The program displays the complete action and requires:

```text
DEPLOY zqjx:DEMO
```

Never put the private key in Python, a notebook, `.env`, a screenshot, shell
history, or this repository.

## 4. Verify the state transition

Do not treat a successful submission response as final verification. Read the
DEX and market back from HyperCore:

```bash
python 01_read_market.py \
  --network testnet \
  --dex zqjx \
  --coin zqjx:DEMO
```

Call the transition verified only when the expected namespace, market,
operator, margin configuration, context, and limits are returned.

## 5. Preview an oracle update

```bash
python 04_oracle_testnet.py \
  --dex zqjx \
  --symbol DEMO \
  --oracle-px 100.12 \
  --mark-px 100.10 \
  --external-perp-px 100.11
```

This prints a sorted `setOracle` action without loading a wallet.

Appending `--execute` requires the private key and the exact confirmation
phrase `ORACLE zqjx:DEMO`. Before publishing, the script verifies that:

- the DEX and market exist;
- the signer is an authorized oracle updater;
- the live `szDecimals` matches the command;
- the DEX has exactly one asset, because this classroom publisher does not
  construct complete multi-asset updates.

For a short cadence demonstration:

```bash
python 04_oracle_testnet.py \
  --dex zqjx \
  --symbol DEMO \
  --oracle-px 100.12 \
  --mark-px 100.10 \
  --external-perp-px 100.11 \
  --iterations 3 \
  --interval 3 \
  --execute
```

A production oracle cannot be a fixed-price classroom loop. It needs
independent sources, contract checks, outlier handling, stale-data alarms, key
isolation, monitoring, and a tested halt-and-settlement runbook.

## Run the tests

```bash
python -m unittest discover -s tests -v
```

The tests cover:

- HYPE native-unit conversion;
- the current `registerAsset2` envelope;
- zero-`maxGas` rejection;
- DEX namespacing and current name length;
- deterministic oracle tuple sorting;
- complete `externalPerpPxs`;
- perpetual price precision.

The same tests run in GitHub Actions on Python 3.10 and 3.13.

## Safety model

| Script | Network | Private key | Signs | Submits by default |
|---|---:|---:|---:|---:|
| `01_read_market.py` | Yes | No | No | No |
| `02_preview_actions.py` | No | No | No | No |
| `03_deploy_testnet.py` | Yes | Only with `--execute` | Only with `--execute` | No |
| `04_oracle_testnet.py` | Only with `--execute` | Only with `--execute` | Only with `--execute` | No |

The write scripts hard-code the testnet API and the testnet signing domain.

## Verified scope

This repository was checked on 2026-07-24 against:

- the official HIP-3 specification;
- the current HIP-3 deployer-action reference;
- the official perpetual info endpoints;
- the official asset-ID documentation;
- `hyperliquid-python-sdk==0.24.0`;
- the live public testnet API.

No successful `registerAsset2` transaction is claimed by this repository.
Until an actual state transition is submitted and read back, deployment and
verification output must not be fabricated.

## Official references

- [HIP-3: Builder-deployed perpetuals](https://hyperliquid.gitbook.io/hyperliquid-docs/hyperliquid-improvement-proposals-hips/hip-3-builder-deployed-perpetuals)
- [HIP-3 deployer actions](https://hyperliquid.gitbook.io/hyperliquid-docs/for-developers/api/hip-3-deployer-actions)
- [Perpetual info endpoints](https://hyperliquid.gitbook.io/hyperliquid-docs/for-developers/api/info-endpoint/perpetuals)
- [Asset IDs](https://hyperliquid.gitbook.io/hyperliquid-docs/for-developers/api/asset-ids)
- [Testnet faucet](https://hyperliquid.gitbook.io/hyperliquid-docs/onboarding/testnet-faucet)
- [Official Python SDK](https://github.com/hyperliquid-dex/hyperliquid-python-sdk)

## License

MIT
