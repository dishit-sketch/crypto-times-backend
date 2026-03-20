"""
On-Chain Whale Monitor for The Crypto Times.

Monitors Bitcoin and Ethereum blockchains for large transactions
and creates NewsArticle objects automatically.

Uses FREE APIs:
  - Bitcoin: mempool.space (no key needed)
  - Ethereum: Etherscan (free tier, needs API key)
  - Prices: CoinGecko (free, no key needed)

What this does in simple terms:
  - Watches every new Bitcoin and Ethereum block
  - When someone moves a LOT of crypto (millions of dollars worth)
  - It creates a news article automatically
  - The article says who sent it, who received it, and how much
  - This is news that breaks BEFORE any journalist writes about it
"""

import logging
import hashlib
import time
import uuid
from datetime import datetime, timedelta, timezone as dt_tz
from decimal import Decimal

import httpx
from django.conf import settings
from django.utils import timezone

from news.models import NewsArticle, Source
from news.scrapers.crypto_filter import is_crypto_related

logger = logging.getLogger("news")


# ═══════════════════════════════════════════════════════════════
# CONFIGURATION — how much crypto counts as "large"
# ═══════════════════════════════════════════════════════════════

# Bitcoin: 1 BTC ≈ $85,000 (as of 2026)
BTC_MIN_AMOUNT = 500          # 500 BTC ≈ $42M — minimum to create alert
BTC_HIGH_AMOUNT = 2000        # 2000 BTC ≈ $170M — high priority
BTC_BREAKING_AMOUNT = 5000    # 5000 BTC ≈ $425M — breaking news

# Ethereum: 1 ETH ≈ $3,500 (as of 2026)
ETH_MIN_AMOUNT = 5000         # 5000 ETH ≈ $17M — minimum
ETH_HIGH_AMOUNT = 20000       # 20000 ETH ≈ $70M — high priority
ETH_BREAKING_AMOUNT = 50000   # 50000 ETH ≈ $175M — breaking news

# Stablecoins (USDT, USDC): 1 coin = $1
STABLE_MIN_AMOUNT = 10_000_000    # $10M minimum
STABLE_HIGH_AMOUNT = 50_000_000   # $50M high priority
STABLE_BREAKING_AMOUNT = 200_000_000  # $200M breaking


# ═══════════════════════════════════════════════════════════════
# KNOWN WALLET ADDRESSES — who owns which wallet
# ═══════════════════════════════════════════════════════════════
# In crypto, wallet addresses are public. We know which addresses
# belong to exchanges, governments, and famous people.

ETH_KNOWN_WALLETS = {
    # Exchanges (where people buy/sell crypto)
    "0x28c6c06298d514db089934071355e5743bf21d60": "Binance",
    "0xf977814e90da44bfa03b6295a0616a897441acec": "Binance",
    "0x21a31ee1afc51d94c2efccaa2092ad1028285549": "Binance",
    "0xdfd5293d8e347dfe59e90efd55b2956a1343963d": "Binance",
    "0xa9d1e08c7793af67e9d92fe308d5697fb81d3e43": "Coinbase",
    "0x503828976d22510aad0201ac7ec88293211d23da": "Coinbase",
    "0x71660c4005ba85c37ccec55d0c4493e66fe775d3": "Coinbase",
    "0x2faf487a4414fe77e2327f0bf4ae2a264a776ad2": "FTX (Bankrupt)",
    "0x267be1c1d684f78cb4f6a176c4911b741e4ffdc0": "Kraken",
    "0x53d284357ec70ce289d6d64134dfac8e511c8a3d": "Kraken",
    "0x6cc5f688a315f3dc28a7781717a9a798a59fda7b": "OKX",
    "0x1ab4973a48dc892cd9971ece8e01dcc7688f8f23": "Bybit",
    "0xf89d7b9c864f589bbf53a82105107622b35eaa40": "Bybit",
    "0x1681195c176239ac5e72d9aebacf5b2492e0c4ee": "Bitfinex",
    "0xdc76cd25977e0a5ae17155770273ad58648900d3": "HTX (Huobi)",
    "0xab5c66752a9e8167967685f1450532fb96d5d24f": "HTX (Huobi)",

    # Stablecoin companies (they print/destroy digital dollars)
    "0x5754284f345afc66a98fbb0a0afe71e0f007b949": "Tether Treasury",
    "0x55fe002aeff02f77364de339a1292923a15844b8": "Circle (USDC)",
    "0x0000000000000000000000000000000000000000": "Burn Address",

    # Famous people / organizations
    "0xd8da6bf26964af9d7eed9e03e53415d37aa96045": "Vitalik Buterin",
    "0xde0b295669a9fd93d5f28d9ec85e40f4cb697bae": "Ethereum Foundation",

    # Government (seized crypto from criminals)
    "0xbc4caf530f40d1006fec3c07e267b05d34631e49": "US Government (DOJ)",
}

BTC_KNOWN_WALLETS = {
    "bc1qm34lsc65zpw79lxes69zkqmk6ee3ewf0j77s3": "Binance",
    "34xp4vRoCGJym3xR7yCVPFHoCNxv4Twseo": "Binance",
    "3FHNBLobJnbCTFTVakh5TXmEneyf5PT61B": "Coinbase",
    "bc1q7cyrfmck2ffu2ud3rn5l5a8yv6f0chkp0zpemf": "Coinbase",
    "1Kr6QSydW9bFQG1mXiPNNu6WpJGmUa9i1g": "Kraken",
    "1HQ3Go3ggs8pFnXuHVHRytPCq5fGG8Hbhx": "Mt. Gox Trustee",
    "15SeCwVCFx5cWyrcdD1Cq1gLWnkExHR4HL": "Mt. Gox Trustee",
    "1KFHE7w8BhaENAswwryaoccDb6qcT6DbYY": "F2Pool (Mining)",
}

# Stablecoin contract addresses on Ethereum
STABLECOIN_CONTRACTS = {
    "0xdac17f958d2ee523a2206206994597c13d831ec7": ("USDT", 6),
    "0xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48": ("USDC", 6),
}


# ═══════════════════════════════════════════════════════════════
# PRICE FETCHER — gets current BTC and ETH prices
# ═══════════════════════════════════════════════════════════════

_price_cache = {"BTC": 0, "ETH": 0, "last_fetch": 0}


def _get_prices() -> dict:
    """Get current BTC and ETH prices from CoinGecko (free API)."""
    now = time.time()
    if now - _price_cache["last_fetch"] < 120:  # Cache for 2 minutes
        return _price_cache

    try:
        resp = httpx.get(
            "https://api.coingecko.com/api/v3/simple/price",
            params={"ids": "bitcoin,ethereum", "vs_currencies": "usd"},
            timeout=10,
        )
        data = resp.json()
        _price_cache["BTC"] = data.get("bitcoin", {}).get("usd", 0)
        _price_cache["ETH"] = data.get("ethereum", {}).get("usd", 0)
        _price_cache["last_fetch"] = now
        logger.info(
            "Whale monitor prices: BTC=$%s ETH=$%s",
            f"{_price_cache['BTC']:,.0f}",
            f"{_price_cache['ETH']:,.0f}",
        )
    except Exception as e:
        logger.warning("Price fetch failed: %s", e)

    return _price_cache


# ═══════════════════════════════════════════════════════════════
# HELPER FUNCTIONS
# ═══════════════════════════════════════════════════════════════

def _lookup_eth_wallet(addr: str) -> str:
    """Look up who owns an Ethereum wallet address."""
    return ETH_KNOWN_WALLETS.get(addr.lower(), "Unknown Wallet")


def _lookup_btc_wallet(addr: str) -> str:
    """Look up who owns a Bitcoin wallet address."""
    return BTC_KNOWN_WALLETS.get(addr, "Unknown Wallet")


def _is_exchange(label: str) -> bool:
    """Check if a wallet belongs to a crypto exchange."""
    exchanges = [
        "Binance", "Coinbase", "Kraken", "OKX", "Bybit",
        "Bitfinex", "HTX", "FTX", "Gate.io",
    ]
    return any(ex in label for ex in exchanges)


def _format_usd(value: float) -> str:
    """Format USD value nicely: $1.5B, $250M, $5M."""
    if value >= 1_000_000_000:
        return f"${value / 1_000_000_000:.1f}B"
    elif value >= 1_000_000:
        return f"${value / 1_000_000:.1f}M"
    else:
        return f"${value:,.0f}"


def _determine_direction(from_label: str, to_label: str) -> str:
    """
    Determine what kind of move this is.
    
    In simple terms:
    - Moving TO an exchange = probably going to sell (bad for price)
    - Moving FROM an exchange = probably holding long term (good for price)
    - Exchange to exchange = usually internal stuff (less interesting)
    - Unknown to unknown = whale moving funds secretly
    """
    from_is_exchange = _is_exchange(from_label)
    to_is_exchange = _is_exchange(to_label)

    if from_is_exchange and to_is_exchange:
        if from_label == to_label:
            return "internal"  # Same exchange moving between wallets — boring
        return "exchange_to_exchange"  # Between exchanges — possible OTC deal
    elif to_is_exchange:
        return "to_exchange"  # Moving to exchange — potential sell pressure
    elif from_is_exchange:
        return "from_exchange"  # Moving from exchange — accumulation
    else:
        return "unknown_transfer"  # Whale to whale — mysterious


def _generate_headline(
    amount: float, asset: str, usd_value: float,
    from_label: str, to_label: str, direction: str,
) -> str:
    """Generate a news headline for the whale alert."""
    usd_str = _format_usd(usd_value)
    amount_str = f"{amount:,.0f}"

    if direction == "to_exchange":
        return f"🐋 {amount_str} {asset} ({usd_str}) deposited to {to_label} — potential sell pressure"
    elif direction == "from_exchange":
        return f"🐋 {amount_str} {asset} ({usd_str}) withdrawn from {from_label} — accumulation signal"
    elif direction == "exchange_to_exchange":
        return f"🐋 {amount_str} {asset} ({usd_str}) moved from {from_label} to {to_label}"
    elif "Tether" in from_label or "Circle" in from_label:
        return f"🐋 {amount_str} {asset} ({usd_str}) minted by {from_label} — new supply entering market"
    elif "Burn" in to_label:
        return f"🐋 {amount_str} {asset} ({usd_str}) burned — supply removed from market"
    elif "Government" in from_label or "Government" in to_label:
        return f"🚨 {amount_str} {asset} ({usd_str}) moved by US Government — seized crypto on the move"
    elif "Mt. Gox" in from_label or "Mt. Gox" in to_label:
        return f"🚨 {amount_str} {asset} ({usd_str}) moved by Mt. Gox Trustee — creditor payments possible"
    else:
        return f"🐋 {amount_str} {asset} ({usd_str}) transferred from {from_label} to {to_label}"


def _generate_description(
    amount: float, asset: str, usd_value: float,
    from_label: str, to_label: str, direction: str,
    tx_hash: str, chain: str,
) -> str:
    """Generate a short news description for the whale alert."""
    usd_str = _format_usd(usd_value)
    amount_str = f"{amount:,.0f}"

    desc = f"A large {asset} transfer of {amount_str} {asset} (worth approximately {usd_str}) "
    desc += f"was detected on the {chain.title()} blockchain. "
    desc += f"The funds moved from {from_label} to {to_label}. "

    if direction == "to_exchange":
        desc += (
            "When large amounts of crypto are deposited to exchanges, "
            "it often signals that the holder may be preparing to sell, "
            "which could create downward price pressure. "
        )
    elif direction == "from_exchange":
        desc += (
            "When large amounts are withdrawn from exchanges, "
            "it typically indicates the holder plans to keep the asset long-term, "
            "which is generally seen as a bullish signal. "
        )
    elif "Government" in from_label or "Government" in to_label:
        desc += (
            "Government wallet movements often involve seized cryptocurrency "
            "from criminal cases and can signal upcoming auctions or transfers. "
        )
    elif "Mt. Gox" in from_label:
        desc += (
            "Mt. Gox was a major Bitcoin exchange that went bankrupt in 2014. "
            "Movements from its trustee wallets may signal creditor repayments. "
        )

    desc += f"Transaction hash: {tx_hash[:20]}..."
    return desc


def _calculate_confidence(
    amount: float, asset: str, usd_value: float,
    from_label: str, to_label: str, direction: str,
) -> float:
    """Calculate confidence score for the whale alert."""
    confidence = 70.0  # Base confidence

    # Higher amounts = more confidence this is newsworthy
    if asset == "BTC" and amount >= BTC_BREAKING_AMOUNT:
        confidence += 20
    elif asset == "ETH" and amount >= ETH_BREAKING_AMOUNT:
        confidence += 20
    elif usd_value >= 100_000_000:
        confidence += 15

    # Known wallets = more confidence
    if from_label != "Unknown Wallet":
        confidence += 5
    if to_label != "Unknown Wallet":
        confidence += 5

    # Government/Mt.Gox = very newsworthy
    if "Government" in from_label or "Mt. Gox" in from_label:
        confidence += 10

    return min(confidence, 98.0)


# ═══════════════════════════════════════════════════════════════
# DEDUPLICATION — prevent same alert twice
# ═══════════════════════════════════════════════════════════════

_seen_tx_hashes = set()
_max_seen = 2000


def _is_duplicate(tx_hash: str) -> bool:
    """Check if we already created an alert for this transaction."""
    global _seen_tx_hashes
    if tx_hash in _seen_tx_hashes:
        return True
    _seen_tx_hashes.add(tx_hash)
    # Prevent memory bloat
    if len(_seen_tx_hashes) > _max_seen:
        _seen_tx_hashes = set(list(_seen_tx_hashes)[-1000:])
    return False


# ═══════════════════════════════════════════════════════════════
# BITCOIN SCANNER — checks latest Bitcoin block
# ═══════════════════════════════════════════════════════════════

def scan_btc_whales(source: Source) -> list[NewsArticle]:
    """
    Scan the latest Bitcoin block for large transactions.
    Uses mempool.space API (completely free, no key needed).
    """
    created = []
    prices = _get_prices()
    btc_price = prices.get("BTC", 0)

    if not btc_price:
        logger.warning("No BTC price — skipping whale scan")
        return created

    try:
        # Get latest block hash
        tip_resp = httpx.get("https://mempool.space/api/blocks/tip/hash", timeout=10)
        tip_hash = tip_resp.text.strip()

        # Get transactions in latest block
        txs_resp = httpx.get(
            f"https://mempool.space/api/block/{tip_hash}/txs",
            timeout=15,
        )
        transactions = txs_resp.json()

        for tx in transactions:
            txid = tx.get("txid", "")

            if _is_duplicate(txid):
                continue

            # Also check database for duplicates
            ext_id = hashlib.sha256(f"whale:btc:{txid}".encode()).hexdigest()[:64]
            if NewsArticle.objects.filter(external_id=ext_id).exists():
                continue

            # Calculate total BTC moved (sum of all outputs)
            total_sats = sum(v.get("value", 0) for v in tx.get("vout", []))
            total_btc = total_sats / 1e8

            if total_btc < BTC_MIN_AMOUNT:
                continue

            usd_value = total_btc * btc_price

            # Find sender (first input address)
            sender_addr = ""
            for vin in tx.get("vin", []):
                addr = vin.get("prevout", {}).get("scriptpubkey_address", "")
                if addr:
                    sender_addr = addr
                    break

            # Find receiver (largest output)
            outputs = sorted(tx.get("vout", []), key=lambda v: v.get("value", 0), reverse=True)
            receiver_addr = outputs[0].get("scriptpubkey_address", "") if outputs else ""

            from_label = _lookup_btc_wallet(sender_addr)
            to_label = _lookup_btc_wallet(receiver_addr)
            direction = _determine_direction(from_label, to_label)

            # Skip boring internal exchange movements
            if direction == "internal":
                continue

            title = _generate_headline(total_btc, "BTC", usd_value, from_label, to_label, direction)
            description = _generate_description(
                total_btc, "BTC", usd_value, from_label, to_label, direction, txid, "bitcoin"
            )
            confidence = _calculate_confidence(total_btc, "BTC", usd_value, from_label, to_label, direction)

            article = NewsArticle.objects.create(
                title=title[:500],
                summary=description[:300],
                content=f"<p>{description}</p>",
                source=source,
                original_url=f"https://mempool.space/tx/{txid}",
                images=[],
                external_id=ext_id,
                category="Markets",
                ai_verdict="REAL",
                confidence_score=confidence,
                status="pending",
            )
            created.append(article)
            logger.info("Whale alert (BTC): %s", title[:60])

    except Exception as e:
        logger.error("BTC whale scan error: %s", e)

    return created


# ═══════════════════════════════════════════════════════════════
# ETHEREUM SCANNER — checks latest Ethereum blocks
# ═══════════════════════════════════════════════════════════════

_last_eth_block = 0


def scan_eth_whales(source: Source) -> list[NewsArticle]:
    """
    Scan recent Ethereum blocks for large ETH transfers.
    Uses Etherscan API (free tier — 5 calls per second).
    """
    global _last_eth_block
    created = []
    prices = _get_prices()
    eth_price = prices.get("ETH", 0)

    etherscan_key = getattr(settings, "ETHERSCAN_API_KEY", "")
    if not etherscan_key:
        logger.debug("ETHERSCAN_API_KEY not set — skipping ETH whale scan")
        return created

    if not eth_price:
        logger.warning("No ETH price — skipping whale scan")
        return created

    try:
        # Get latest block number
        resp = httpx.get(
            "https://api.etherscan.io/v2/api",
            params={
                "chainid": "1",
                "module": "proxy",
                "action": "eth_blockNumber",
                "apikey": etherscan_key,
            },
            timeout=10,
        )
        current_block = int(resp.json().get("result", "0x0"), 16)

        if _last_eth_block == 0:
            _last_eth_block = current_block - 2  # Start from 2 blocks ago

        if current_block <= _last_eth_block:
            return created

        # Scan last few blocks (max 3 at a time to stay within rate limits)
        for block_num in range(_last_eth_block + 1, min(current_block + 1, _last_eth_block + 4)):
            time.sleep(0.3)  # Rate limit: 5 calls/sec on free tier

            block_resp = httpx.get(
                "https://api.etherscan.io/v2/api",
                params={
                    "chainid": "1",
                    "module": "proxy",
                    "action": "eth_getBlockByNumber",
                    "tag": hex(block_num),
                    "boolean": "true",
                    "apikey": etherscan_key,
                },
                timeout=15,
            )

            block = block_resp.json().get("result", {})
            if not block or not block.get("transactions"):
                continue

            for tx in block.get("transactions", []):
                value_wei = int(tx.get("value", "0x0"), 16)
                value_eth = value_wei / 1e18

                if value_eth < ETH_MIN_AMOUNT:
                    continue

                tx_hash = tx.get("hash", "")
                if _is_duplicate(tx_hash):
                    continue

                ext_id = hashlib.sha256(f"whale:eth:{tx_hash}".encode()).hexdigest()[:64]
                if NewsArticle.objects.filter(external_id=ext_id).exists():
                    continue

                usd_value = value_eth * eth_price
                from_addr = tx.get("from", "")
                to_addr = tx.get("to", "") or ""

                from_label = _lookup_eth_wallet(from_addr)
                to_label = _lookup_eth_wallet(to_addr)
                direction = _determine_direction(from_label, to_label)

                if direction == "internal":
                    continue

                title = _generate_headline(value_eth, "ETH", usd_value, from_label, to_label, direction)
                description = _generate_description(
                    value_eth, "ETH", usd_value, from_label, to_label, direction, tx_hash, "ethereum"
                )
                confidence = _calculate_confidence(
                    value_eth, "ETH", usd_value, from_label, to_label, direction
                )

                article = NewsArticle.objects.create(
                    title=title[:500],
                    summary=description[:300],
                    content=f"<p>{description}</p>",
                    source=source,
                    original_url=f"https://etherscan.io/tx/{tx_hash}",
                    images=[],
                    external_id=ext_id,
                    category="Markets",
                    ai_verdict="REAL",
                    confidence_score=confidence,
                    status="pending",
                )
                created.append(article)
                logger.info("Whale alert (ETH): %s", title[:60])

        _last_eth_block = current_block

    except Exception as e:
        logger.error("ETH whale scan error: %s", e)

    return created


# ═══════════════════════════════════════════════════════════════
# MAIN SCRAPER FUNCTION — called by orchestrator
# ═══════════════════════════════════════════════════════════════

def scrape_whale_source(source: Source) -> list[NewsArticle]:
    """
    Main entry point — called by the orchestrator every 5 minutes.
    Scans both Bitcoin and Ethereum for large transactions.
    """
    logger.info("Whale monitor: scanning BTC + ETH blockchains...")
    created = []

    # Scan Bitcoin
    btc_articles = scan_btc_whales(source)
    created.extend(btc_articles)

    # Scan Ethereum (only if API key is set)
    eth_articles = scan_eth_whales(source)
    created.extend(eth_articles)

    logger.info(
        "Whale monitor complete: %d BTC alerts, %d ETH alerts",
        len(btc_articles), len(eth_articles),
    )

    # Update last fetched
    source.last_fetched_at = timezone.now()
    source.save(update_fields=["last_fetched_at"])

    return created
