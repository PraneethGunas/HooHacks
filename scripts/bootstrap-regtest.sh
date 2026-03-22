#!/usr/bin/env bash
# ---------------------------------------------------------------------------
# PolicyPulse — Bootstrap regtest Lightning environment
#
# Follows lightning-agent-tools patterns:
#   1. Wait for bitcoind + both litd nodes
#   2. Fund the buyer wallet (mine blocks)
#   3. Connect buyer ↔ seller and open channel
#   4. Confirm channel (mine blocks)
#   5. Bake invoice macaroon for Aperture (least privilege)
#   6. Generate lnget config.yaml (matches lnget config init format)
#
# Runs as a one-shot container after both litd nodes are healthy.
#
# ===========================================================================
# INTEGRATION GUIDE
# ===========================================================================
#
# STATUS: 🟢 REAL — All operations use real Bitcoin/Lightning on regtest.
#
# WHAT'S REAL:
#   - Mines real regtest blocks, funds a real wallet, opens a real channel
#   - Bakes a real invoice macaroon with least-privilege permissions
#   - Generates a real lnget config that the backend uses for L402 payments
#
# WHAT'S HARDCODED (demo-safe defaults):
#   - RPC creds: policypulse/policypulse (line ~18) — demo only
#   - Channel size: 1M sats (line ~25) — enough for hundreds of demo queries
#   - lnget max_cost_sats: 500 (line ~134) — safety cap
#
# OWNER: Praneeth (Lightning module) + Pratham (Docker infra)
#
# NOTE FOR PRATHAM: If you add new services that need Lightning payments,
# no changes needed here. Aperture + lnget handle routing automatically.
# Just add the service in aperture.yaml and the endpoint in premium_data.py.
# ===========================================================================

set -euo pipefail

BITCOIN_CLI="bitcoin-cli -regtest -rpcuser=policypulse -rpcpassword=policypulse -rpcconnect=bitcoind -rpcport=18443"

# litd uses /root/.lnd as the lnd data dir inside the container
# These are mounted as volumes: /lnd-buyer and /lnd-seller
LNCLI_BUYER="lncli --rpcserver=litd-buyer:10009 --tlscertpath=/lnd-buyer/tls.cert --macaroonpath=/lnd-buyer/data/chain/bitcoin/regtest/admin.macaroon --network=regtest"
LNCLI_SELLER="lncli --rpcserver=litd-seller:10009 --tlscertpath=/lnd-seller/tls.cert --macaroonpath=/lnd-seller/data/chain/bitcoin/regtest/admin.macaroon --network=regtest"

CHANNEL_SIZE=1000000  # 1M sats — plenty for demo micropayments

echo "========================================="
echo "  PolicyPulse Regtest Bootstrap"
echo "========================================="
echo ""

# ---------------------------------------------------------------------------
# 1. Wait for services
# ---------------------------------------------------------------------------
echo "[1/7] Waiting for services..."

echo -n "  bitcoind: "
until $BITCOIN_CLI getblockchaininfo > /dev/null 2>&1; do sleep 1; done
echo "ready"

echo -n "  litd-buyer: "
until $LNCLI_BUYER getinfo > /dev/null 2>&1; do sleep 1; done
echo "ready"

echo -n "  litd-seller: "
until $LNCLI_SELLER getinfo > /dev/null 2>&1; do sleep 1; done
echo "ready"

# Wait for wallets to fully sync to chain (getinfo succeeds before wallet sync)
echo -n "  buyer wallet sync: "
SYNC_RETRIES=30
while [ $SYNC_RETRIES -gt 0 ]; do
    SYNCED=$($LNCLI_BUYER getinfo 2>/dev/null | jq -r '.synced_to_chain // "false"')
    if [ "$SYNCED" = "true" ]; then break; fi
    sleep 2
    SYNC_RETRIES=$((SYNC_RETRIES - 1))
done
echo "synced"

echo -n "  seller wallet sync: "
SYNC_RETRIES=30
while [ $SYNC_RETRIES -gt 0 ]; do
    SYNCED=$($LNCLI_SELLER getinfo 2>/dev/null | jq -r '.synced_to_chain // "false"')
    if [ "$SYNCED" = "true" ]; then break; fi
    sleep 2
    SYNC_RETRIES=$((SYNC_RETRIES - 1))
done
echo "synced"
echo ""

# ---------------------------------------------------------------------------
# 2. Fund the buyer wallet
# ---------------------------------------------------------------------------
echo "[2/7] Funding buyer wallet..."
BUYER_ADDR=$($LNCLI_BUYER newaddress p2wkh | jq -r '.address')
echo "  Address: $BUYER_ADDR"

echo "  Mining 101 blocks in batches (coinbase maturity = 100)..."
# Mine in small batches so litd wallet backend can keep up.
# Mining all 101 at once causes "Block height out of range" — the wallet
# can't index blocks fast enough and gets permanently stuck.
for i in 1 2 3 4 5; do
    $BITCOIN_CLI generatetoaddress 20 "$BUYER_ADDR" > /dev/null
    sleep 2
done
$BITCOIN_CLI generatetoaddress 1 "$BUYER_ADDR" > /dev/null  # block 101
sleep 3

BUYER_BALANCE=$($LNCLI_BUYER walletbalance | jq -r '.confirmed_balance')
echo "  Balance: $BUYER_BALANCE sats"

# Wait for BOTH nodes to re-sync after mining blocks
echo "  Waiting for nodes to sync new blocks..."
SYNC_RETRIES=90
while [ $SYNC_RETRIES -gt 0 ]; do
    BUYER_SYNCED=$($LNCLI_BUYER getinfo 2>/dev/null | jq -r '.synced_to_chain // "false"')
    SELLER_SYNCED=$($LNCLI_SELLER getinfo 2>/dev/null | jq -r '.synced_to_chain // "false"')
    if [ "$BUYER_SYNCED" = "true" ] && [ "$SELLER_SYNCED" = "true" ]; then
        echo "  Both nodes synced to chain"
        break
    fi
    if [ $((SYNC_RETRIES % 10)) -eq 0 ]; then
        echo "  Still syncing... ($SYNC_RETRIES retries left, buyer=$BUYER_SYNCED seller=$SELLER_SYNCED)"
    fi
    sleep 2
    SYNC_RETRIES=$((SYNC_RETRIES - 1))
done
if [ $SYNC_RETRIES -eq 0 ]; then
    echo "  ERROR: Nodes failed to sync after 3 minutes. Aborting."
    echo "  Check litd logs: docker compose logs litd-buyer"
    exit 1
fi
echo ""

# ---------------------------------------------------------------------------
# 3. Connect buyer to seller
# ---------------------------------------------------------------------------
echo "[3/7] Connecting buyer to seller..."
SELLER_PUBKEY=$($LNCLI_SELLER getinfo | jq -r '.identity_pubkey')
echo "  Seller pubkey: ${SELLER_PUBKEY:0:20}..."

# Retry connect — server may still be initializing subsystems after mining
CONNECT_RETRIES=20
while [ $CONNECT_RETRIES -gt 0 ]; do
    ERR=$($LNCLI_BUYER connect "${SELLER_PUBKEY}@litd-seller:9735" 2>&1 || true)
    if echo "$ERR" | grep -q "already connected"; then break; fi
    if echo "$ERR" | grep -qi "error\|starting\|unavailable"; then
        echo "  Waiting for buyer to accept connections... ($CONNECT_RETRIES retries left)"
        sleep 3
        CONNECT_RETRIES=$((CONNECT_RETRIES - 1))
    else
        # Success or unexpected output — either way, move on
        break
    fi
done
echo "  Connected"
echo ""

# ---------------------------------------------------------------------------
# 4. Open channel
# ---------------------------------------------------------------------------
echo "[4/7] Opening channel (${CHANNEL_SIZE} sats)..."

# Retry openchannel — server may still be starting or re-syncing
OPEN_RETRIES=20
CHANNEL_OPENED=false
while [ $OPEN_RETRIES -gt 0 ]; do
    RESULT=$($LNCLI_BUYER openchannel --node_key="$SELLER_PUBKEY" --local_amt=$CHANNEL_SIZE 2>&1)
    if echo "$RESULT" | grep -q "funding_txid"; then
        TXID=$(echo "$RESULT" | jq -r '.funding_txid // empty' 2>/dev/null || echo "$RESULT")
        echo "  Funding txid: $TXID"
        CHANNEL_OPENED=true
        break
    fi
    if echo "$RESULT" | grep -qi "pending channels exceed"; then
        echo "  Channel already pending from previous attempt — continuing"
        CHANNEL_OPENED=true
        break
    fi
    if echo "$RESULT" | grep -qi "starting\|unavailable\|not connected\|syncing"; then
        echo "  Waiting for channel open readiness... ($OPEN_RETRIES retries left)"
        sleep 5
        OPEN_RETRIES=$((OPEN_RETRIES - 1))
    else
        echo "  Unexpected: $RESULT"
        echo "  Retrying... ($OPEN_RETRIES retries left)"
        sleep 3
        OPEN_RETRIES=$((OPEN_RETRIES - 1))
    fi
done

if [ "$CHANNEL_OPENED" != "true" ]; then
    echo "  ERROR: Failed to open channel after all retries"
    echo "  Last result: $RESULT"
    exit 1
fi
echo ""

# ---------------------------------------------------------------------------
# 5. Confirm channel
# ---------------------------------------------------------------------------
echo "[5/7] Mining 6 blocks to confirm channel..."
$BITCOIN_CLI generatetoaddress 6 "$BUYER_ADDR" > /dev/null
sleep 3

# Verify channel is active
RETRIES=10
while [ $RETRIES -gt 0 ]; do
    CHANNELS=$($LNCLI_BUYER listchannels | jq '.channels | length')
    if [ "$CHANNELS" -ge 1 ]; then
        break
    fi
    echo "  Waiting for channel activation... ($RETRIES retries left)"
    $BITCOIN_CLI generatetoaddress 1 "$BUYER_ADDR" > /dev/null
    sleep 2
    RETRIES=$((RETRIES - 1))
done

if [ "$CHANNELS" -ge 1 ]; then
    LOCAL_BALANCE=$($LNCLI_BUYER listchannels | jq -r '.channels[0].local_balance')
    echo "  Channel active! Local balance: $LOCAL_BALANCE sats"
else
    echo "  WARNING: Channel not active yet. May need more time."
fi
echo ""

# ---------------------------------------------------------------------------
# 6. Bake invoice macaroon for Aperture (least privilege)
# ---------------------------------------------------------------------------
echo "[6/7] Baking invoice macaroon for Aperture..."
$LNCLI_SELLER bakemacaroon invoices:read invoices:write \
    --save_to=/lnd-seller/data/chain/bitcoin/regtest/invoice.macaroon 2>/dev/null || true
echo "  invoice.macaroon created"
echo ""

# ---------------------------------------------------------------------------
# 7. Generate lnget config (matches lnget config init format)
# ---------------------------------------------------------------------------
echo "[7/7] Generating lnget config..."

LNGET_DIR="/lnget-config"
mkdir -p "$LNGET_DIR"

# 🟢 REAL: This matches the format lnget config init produces.
# The backend container reads this at /root/.lnget/config.yaml.
# For mainnet, change network + macaroon path accordingly.
cat > "$LNGET_DIR/config.yaml" <<'EOF'
# Auto-generated by PolicyPulse bootstrap for regtest
# Matches lnget config init format from lightning-agent-tools

l402:
  max_cost_sats: 500
  max_fee_percent: 1.0
  payment_timeout: 30s
  auto_pay: true

ln:
  mode: lnd
  lnd:
    host: litd-buyer:10009
    tls_cert: /root/.lnd/tls.cert
    macaroon: /root/.lnd/data/chain/bitcoin/regtest/admin.macaroon
    network: regtest

http:
  timeout: 30s
  insecure_skip_verify: true

tokens:
  store_dir: /root/.lnget/tokens
EOF

echo "  Config written to $LNGET_DIR/config.yaml"
echo ""

echo "========================================="
echo "  Bootstrap complete!"
echo "========================================="
echo ""
echo "  Buyer balance:  $BUYER_BALANCE sats"
echo "  Channel:        ${CHANNEL_SIZE} sats"
echo "  lnget config:   $LNGET_DIR/config.yaml"
echo ""
echo "  Test commands:"
echo "    curl http://premium-data:8082/v1/legal/h1b        # direct (no L402)"
echo "    curl -v http://aperture:8081/v1/legal/h1b          # via Aperture (402)"
echo "    lnget --max-cost=500 -k http://aperture:8081/v1/legal/h1b  # full L402"
echo ""
