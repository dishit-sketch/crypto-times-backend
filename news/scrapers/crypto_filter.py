"""
Crypto relevance filter.
Used by scrapers to skip non-crypto articles from general news sources.
"""

# Keywords that indicate an article is crypto-related
CRYPTO_KEYWORDS = [
    # Coins & tokens
    "bitcoin", "btc", "ethereum", "eth", "solana", "sol", "cardano", "ada",
    "ripple", "xrp", "dogecoin", "doge", "polkadot", "avalanche", "polygon",
    "matic", "chainlink", "litecoin", "tron", "shiba", "pepe", "memecoin",
    "altcoin", "stablecoin", "usdt", "usdc", "tether", "dai",

    # Core concepts
    "crypto", "cryptocurrency", "blockchain", "web3", "defi", "nft",
    "token", "mining", "staking", "airdrop", "halving", "hash rate",
    "smart contract", "decentralized", "layer 2", "layer-2", "l2",
    "proof of stake", "proof of work", "consensus",

    # DeFi
    "uniswap", "aave", "compound", "makerdao", "lido", "curve",
    "liquidity pool", "yield farming", "dex", "amm", "tvl",
    "total value locked", "lending protocol",

    # Exchanges & companies
    "coinbase", "binance", "kraken", "gemini", "ftx", "bitfinex",
    "microstrategy", "grayscale", "blackrock etf", "bitcoin etf",
    "spot etf", "crypto exchange",

    # Regulation & legal
    "sec crypto", "cftc crypto", "crypto regulation", "crypto ban",
    "crypto tax", "cbdc", "digital dollar", "digital euro",
    "digital currency", "central bank digital",

    # Market terms
    "crypto market", "bitcoin price", "eth price", "bull run",
    "bear market", "crypto crash", "crypto rally", "whale",
    "on-chain", "off-chain", "gas fee", "gas fees",

    # Security
    "crypto hack", "rug pull", "crypto scam", "phishing crypto",
    "exploit", "bridge hack", "wallet hack",

    # People
    "satoshi", "vitalik", "cz binance", "michael saylor",
    "gary gensler", "sam bankman",
]


def is_crypto_related(title: str, summary: str = "") -> bool:
    """
    Check if an article is related to cryptocurrency.
    Returns True if any crypto keyword is found in title or summary.
    """
    text = (title + " " + summary).lower()

    for keyword in CRYPTO_KEYWORDS:
        if keyword in text:
            return True

    return False
