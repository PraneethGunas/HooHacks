#!/bin/bash
# ============================================================
# mine_blocks.sh
# Mine N regtest blocks (default: 1) to confirm transactions.
#
# Usage: ./docker/scripts/mine_blocks.sh [N]
# ============================================================

N=${1:-1}
BITCOIN_CLI="docker compose exec bitcoind bitcoin-cli -regtest -rpcuser=bitcoin -rpcpassword=bitcoin"

ADDR=$($BITCOIN_CLI getnewaddress)
$BITCOIN_CLI generatetoaddress $N $ADDR
echo "⛏️  Mined $N block(s)"
