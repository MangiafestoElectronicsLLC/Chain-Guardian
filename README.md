# Chain-Guardian

A user-friendly, Tkinter-powered application for tracking crypto assets, monitoring whale wallets, analyzing real-time prices, visualizing portfolio gains/losses, and securely storing wallet data using Fernet encryption.

Features

Real-time crypto price tracking

Tracks BTC/ETH top 100 whale wallets

Built-in profit-taking logic (e.g., auto-alert at 300% gain)

Fear & Greed Index integration

Easy GUI with charts & live portfolio metrics

Secure storage of wallet addresses and API keys using Fernet

Auto-calculated average buy price, total value, and historical gains

Works with hardware wallet public addresses (no private keys required)

# Chain Guardian Added Features

Chain Guardian is a modular, encrypted, multi-wallet crypto monitoring toolkit:
- Encrypted storage (Fernet) for API keys, addresses, and app data
- Portfolio analytics (avg cost, realized/unrealized P&L)
- Profit-take signals (configurable; default: 300% -> withdraw original investment)
- Fear & Greed integration
- Basic whale address tracking (BTC/ETH) via public APIs (Blockchair / Etherscan)
- Tk GUI + Matplotlib helpers (starter app)

## Quick start

1. Clone repo:
   ```bash
   git clone https://github.com/YOUR_USERNAME/chain-guardian.git
   cd chain-guardian

2. Create venv and install:

python -m venv venv
source venv/bin/activate # Windows: venv\Scripts\activate
pip install -r requirements.txt


3. Run the app:

python -m chainguardian.main



First run will create a directory ~/.chainguardian/ containing:

fernet.key (local encryption key) — do not commit

store.enc (encrypted data store)


Adding API keys & tracked addresses

The GUI exposes a "Manage API Keys" dialog (or edit config later).

For Etherscan: add under Etherscan key.

For Blockchair: add key if you have one; otherwise paste addresses manually under Manage Addresses in the GUI.


Security notes

Fernet key is stored locally. Back it up securely.

Do not commit your keys, backups, or .env with secrets.

The app is advisory-only by default. No live trading unless you wire CCXT order placement intentionally.
