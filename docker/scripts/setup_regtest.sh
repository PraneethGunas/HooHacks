#!/bin/bash
# ============================================================
# setup_regtest.sh
# Run once after `docker compose up` to fund the LND wallet
# and get the Lightning node ready for L402 payments.
#
# Usage: ./docker/scripts/setup_regtest.sh
# ============================================================

set -e

BITCOIN_CLI="docker compose exec bitcoind bitcoin-cli -regtest -rpcuser=bitcoin -rpcpassword=bitcoin"
LND_CLI="docker compose exec lnd lncli --network=regtest"

echo "⏳ Waiting for LND to be ready..."
until docker compose exec lnd lncli --network=regtest getinfo &>/dev/null; do
  sleep 3
done
echo "✅ LND is up"

echo ""
echo "📦 Creating LND wallet (if not already created)..."
# Only runs if wallet doesn't exist — safe to call multiple times
$LND_CLI create 2>/dev/null || echo "   (wallet already exists, skipping)"

echo ""
echo "⛏️  Mining initial blocks to fund wallet..."
# Get a Bitcoin address from LND to fund
LND_ADDRESS=$($LND_CLI newaddress p2wkh | python3 -c "import sys,json; print(json.load(sys.stdin)['address'])")
echo "   LND funding address: $LND_ADDRESS"

# Mine 101 blocks (100 to make coinbase spendable + 1 extra)
$BITCOIN_CLI generatetoaddress 101 $LND_ADDRESS
echo "   ✅ Mined 101 regtest blocks"

echo ""
echo "💰 LND wallet balance:"
$LND_CLI walletbalance

echo ""
echo "🎉 Regtest setup complete! LND is funded and ready for L402 payments."
echo ""
echo "   To mine more blocks:  ./docker/scripts/mine_blocks.sh 10"
echo "   To check LND status:  docker compose exec lnd lncli --network=regtest getinfo"
