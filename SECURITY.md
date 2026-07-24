# Security

This repository is an educational testnet lab, not audited deployment or
oracle infrastructure.

- Use a disposable testnet-only wallet.
- Never reuse a production deployer, oracle, or trading key.
- Never commit a private key, `.env` file, keystore, or shell transcript.
- The read and preview exercises do not need a private key.
- The state-changing exercises require both `--execute` and an explicit
  confirmation.
- Recheck the current Hyperliquid documentation, auction, collateral mapping,
  margin configuration, and oracle requirements before every deployment.

If a key is exposed, stop using it immediately and replace any authority it
holds. Do not include secrets in a public issue.

