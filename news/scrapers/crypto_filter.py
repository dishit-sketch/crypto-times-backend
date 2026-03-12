"""
Strict crypto relevance filter.
Only allows articles that are clearly about cryptocurrency.
"""

# HIGH confidence keywords — if found in TITLE, article is crypto
TITLE_KEYWORDS = [
    "bitcoin", "btc", "ethereum", "eth", "solana", "sol", "cardano",
    "ripple", "xrp", "dogecoin", "doge", "polygon", "matic", "chainlink",
    "litecoin", "avalanche", "polkadot", "tron", "shiba inu", "pepe coin",
    "memecoin", "altcoin", "stablecoin", "usdt", "usdc", "tether",
    "crypto", "cryptocurrency", "blockchain", "web3", "defi", "nft",
    "token", "mining", "staking", "airdrop", "halving",
    "smart contract", "decentralized", "layer 2", "layer-2",
    "uniswap", "aave", "compound", "makerdao", "lido", "curve",
    "coinbase", "binance", "kraken", "gemini", "bitfinex",
    "microstrategy", "grayscale", "bitcoin etf", "spot etf",
    "crypto exchange", "crypto market", "crypto regulation",
    "cbdc", "digital currency", "central bank digital",
    "on-chain", "gas fee", "rug pull", "crypto hack",
    "satoshi", "vitalik", "saylor",
]

# MEDIUM confidence — only counts if found with another keyword
SUPPORTING_KEYWORDS = [
    "wallet", "ledger", "node", "validator", "consensus",
    "proof of stake", "proof of work", "hash rate",
    "bull run", "bear market", "whale", "liquidation",
    "sec", "cftc", "regulation", "compliance",
    "digital asset", "virtual currency", "distributed ledger",
    "dex", "amm", "tvl", "yield", "liquidity pool",
    "protocol", "mainnet", "testnet", "fork", "upgrade",
    "exchange", "trading", "market cap",
]


def is_crypto_related(title: str, summary: str = "") -> bool:
    """
    Strict check if an article is about cryptocurrency.
    
    Rules:
    1. If title contains any TITLE_KEYWORD → YES
    2. If title contains 2+ SUPPORTING_KEYWORDS → YES
    3. If summary contains 2+ TITLE_KEYWORDS → YES
    4. Otherwise → NO
    """
    title_lower = title.lower()
    summary_lower = summary.lower()

    # Rule 1: Title has a strong crypto keyword
    for kw in TITLE_KEYWORDS:
        if kw in title_lower:
            return True

    # Rule 2: Title has 2+ supporting keywords
    title_support_count = sum(1 for kw in SUPPORTING_KEYWORDS if kw in title_lower)
    if title_support_count >= 2:
        return True

    # Rule 3: Summary has 2+ strong keywords
    summary_strong_count = sum(1 for kw in TITLE_KEYWORDS if kw in summary_lower)
    if summary_strong_count >= 2:
        return True

    return False
