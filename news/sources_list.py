"""
100+ Original crypto news sources for CryptoTimes.io
Only primary/original sources — no competitor crypto news sites.
Auto-loaded on server startup.
"""

STARTER_SOURCES = [
    # ════════════════════════════════════════════════════════
    # OFFICIAL GOVERNMENT & REGULATORY
    # ════════════════════════════════════════════════════════
    {"name": "SEC Press Releases", "type": "rss", "url": "https://www.sec.gov/news/pressreleases.rss", "description": "Official SEC press releases — crypto enforcement, ETF approvals.", "reliability_score": 98},
    {"name": "Federal Reserve", "type": "rss", "url": "https://www.federalreserve.gov/feeds/press_all.xml", "description": "Federal Reserve — interest rates, CBDC, monetary policy.", "reliability_score": 99},
    {"name": "US Treasury", "type": "rss", "url": "https://home.treasury.gov/system/files/136/treasury-rss.xml", "description": "US Treasury — sanctions, stablecoin policy, financial regulation.", "reliability_score": 98},
    {"name": "CFTC Press", "type": "rss", "url": "https://www.cftc.gov/Newsroom/PressReleases/RSS", "description": "CFTC — crypto derivatives regulation, enforcement.", "reliability_score": 97},
    {"name": "EU Blockchain Observatory", "type": "rss", "url": "https://www.eublockchainforum.eu/rss.xml", "description": "EU blockchain policy and MiCA regulation updates.", "reliability_score": 93},

    # ════════════════════════════════════════════════════════
    # OFFICIAL BLOCKCHAIN PROTOCOL SOURCES
    # ════════════════════════════════════════════════════════
    {"name": "Ethereum Foundation Blog", "type": "rss", "url": "https://blog.ethereum.org/feed.xml", "description": "Official Ethereum updates — upgrades, research, EIPs.", "reliability_score": 97},
    {"name": "Solana News", "type": "rss", "url": "https://solana.com/news/rss.xml", "description": "Official Solana — network updates, ecosystem growth.", "reliability_score": 95},
    {"name": "Polygon Blog", "type": "rss", "url": "https://blog.polygon.technology/feed/", "description": "Polygon — zkEVM, scaling solutions, partnerships.", "reliability_score": 94},
    {"name": "Avalanche Blog", "type": "rss", "url": "https://medium.com/feed/avalancheavax", "description": "Avalanche — subnets, DeFi ecosystem updates.", "reliability_score": 93},
    {"name": "Chainlink Blog", "type": "rss", "url": "https://blog.chain.link/feed/", "description": "Chainlink — oracles, CCIP, data feeds.", "reliability_score": 94},
    {"name": "Cosmos Blog", "type": "rss", "url": "https://blog.cosmos.network/feed", "description": "Cosmos — IBC, appchains, interoperability.", "reliability_score": 92},
    {"name": "Polkadot Blog", "type": "rss", "url": "https://medium.com/feed/polkadot-network", "description": "Polkadot — parachains, governance, JAM.", "reliability_score": 93},
    {"name": "Arbitrum Blog", "type": "rss", "url": "https://medium.com/feed/offchainlabs", "description": "Arbitrum — L2 scaling, Orbit chains.", "reliability_score": 93},
    {"name": "Optimism Blog", "type": "rss", "url": "https://medium.com/feed/ethereum-optimism", "description": "Optimism — OP Stack, Superchain, L2 updates.", "reliability_score": 93},
    {"name": "Near Protocol Blog", "type": "rss", "url": "https://medium.com/feed/nearprotocol", "description": "Near — chain abstraction, AI integration.", "reliability_score": 91},
    {"name": "Aptos Blog", "type": "rss", "url": "https://medium.com/feed/aptoslabs", "description": "Aptos — Move language, network updates.", "reliability_score": 90},
    {"name": "Sui Blog", "type": "rss", "url": "https://blog.sui.io/feed", "description": "Sui — parallel execution, object model.", "reliability_score": 90},

    # ════════════════════════════════════════════════════════
    # MAJOR EXCHANGES & COMPANIES (Official Blogs)
    # ════════════════════════════════════════════════════════
    {"name": "Coinbase Blog", "type": "rss", "url": "https://www.coinbase.com/blog/rss", "description": "Coinbase — product launches, Base L2, compliance.", "reliability_score": 91},
    {"name": "Binance Blog", "type": "rss", "url": "https://www.binance.com/en/feed/rss", "description": "Binance — listings, BNB Chain, security.", "reliability_score": 85},
    {"name": "Kraken Blog", "type": "rss", "url": "https://blog.kraken.com/feed", "description": "Kraken — exchange updates, market insights.", "reliability_score": 90},
    {"name": "OKX Blog", "type": "rss", "url": "https://www.okx.com/academy/en/feed", "description": "OKX — Web3 wallet, DEX aggregator.", "reliability_score": 86},
    {"name": "Bitfinex Blog", "type": "rss", "url": "https://blog.bitfinex.com/feed/", "description": "Bitfinex — trading, Tether updates.", "reliability_score": 84},
    {"name": "Ripple Insights", "type": "rss", "url": "https://ripple.com/insights/feed/", "description": "Ripple — XRP, cross-border payments, RLUSD.", "reliability_score": 89},
    {"name": "Circle Blog", "type": "rss", "url": "https://www.circle.com/blog/rss.xml", "description": "Circle — USDC stablecoin, compliance.", "reliability_score": 92},
    {"name": "Tether News", "type": "rss", "url": "https://tether.to/en/rss/", "description": "Tether — USDT reserves, transparency reports.", "reliability_score": 80},
    {"name": "MicroStrategy IR", "type": "rss", "url": "https://www.microstrategy.com/press/feed", "description": "MicroStrategy — Bitcoin treasury, corporate strategy.", "reliability_score": 93},
    {"name": "Galaxy Digital Research", "type": "rss", "url": "https://www.galaxy.com/research/feed/", "description": "Galaxy Digital — institutional crypto research.", "reliability_score": 91},

    # ════════════════════════════════════════════════════════
    # DEFI PROTOCOL BLOGS
    # ════════════════════════════════════════════════════════
    {"name": "Uniswap Blog", "type": "rss", "url": "https://blog.uniswap.org/rss", "description": "Uniswap — AMM updates, governance, Unichain.", "reliability_score": 93},
    {"name": "Aave Blog", "type": "rss", "url": "https://medium.com/feed/aave", "description": "Aave — lending protocol, GHO stablecoin.", "reliability_score": 92},
    {"name": "MakerDAO Blog", "type": "rss", "url": "https://blog.makerdao.com/feed/", "description": "MakerDAO — DAI, RWA, Sky protocol.", "reliability_score": 93},
    {"name": "Lido Blog", "type": "rss", "url": "https://blog.lido.fi/rss/", "description": "Lido — liquid staking, stETH.", "reliability_score": 91},
    {"name": "Compound Blog", "type": "rss", "url": "https://medium.com/feed/compound-finance", "description": "Compound — lending, governance.", "reliability_score": 91},
    {"name": "Curve Blog", "type": "rss", "url": "https://news.curve.fi/rss/", "description": "Curve — stablecoin DEX, crvUSD.", "reliability_score": 90},
    {"name": "dYdX Blog", "type": "rss", "url": "https://dydx.exchange/blog/feed", "description": "dYdX — perpetuals, decentralized derivatives.", "reliability_score": 89},
    {"name": "Yearn Finance", "type": "rss", "url": "https://medium.com/feed/iearn", "description": "Yearn — yield vaults, strategies.", "reliability_score": 88},
    {"name": "1inch Blog", "type": "rss", "url": "https://blog.1inch.io/feed", "description": "1inch — DEX aggregation, Fusion.", "reliability_score": 88},

    # ════════════════════════════════════════════════════════
    # ON-CHAIN DATA & ANALYTICS
    # ════════════════════════════════════════════════════════
    {"name": "Glassnode Insights", "type": "rss", "url": "https://insights.glassnode.com/rss/", "description": "On-chain analytics — BTC/ETH market intelligence.", "reliability_score": 94},
    {"name": "Chainalysis Blog", "type": "rss", "url": "https://blog.chainalysis.com/feed/", "description": "Blockchain analytics — crime, compliance, research.", "reliability_score": 95},
    {"name": "Dune Analytics Blog", "type": "rss", "url": "https://dune.com/blog/feed", "description": "Dune — community analytics, dashboards.", "reliability_score": 90},
    {"name": "Nansen Research", "type": "rss", "url": "https://www.nansen.ai/research/rss", "description": "Nansen — smart money tracking, alpha.", "reliability_score": 91},
    {"name": "Messari Blog", "type": "rss", "url": "https://messari.io/rss", "description": "Messari — crypto research, governance.", "reliability_score": 92},
    {"name": "DeFi Llama Blog", "type": "rss", "url": "https://medium.com/feed/defillama", "description": "DeFi Llama — TVL data, protocol analytics.", "reliability_score": 90},
    {"name": "IntoTheBlock Blog", "type": "rss", "url": "https://medium.com/feed/intotheblock", "description": "IntoTheBlock — on-chain indicators, analytics.", "reliability_score": 89},

    # ════════════════════════════════════════════════════════
    # SECURITY & AUDIT FIRMS
    # ════════════════════════════════════════════════════════
    {"name": "SlowMist Blog", "type": "rss", "url": "https://medium.com/feed/@pikicast-slowmist", "description": "SlowMist — security incidents, hack analysis.", "reliability_score": 93},
    {"name": "CertiK Blog", "type": "rss", "url": "https://www.certik.com/resources/blog/rss", "description": "CertiK — smart contract audits, security.", "reliability_score": 91},
    {"name": "OpenZeppelin Blog", "type": "rss", "url": "https://blog.openzeppelin.com/feed", "description": "OpenZeppelin — smart contract security, tools.", "reliability_score": 94},
    {"name": "Immunefi Blog", "type": "rss", "url": "https://medium.com/feed/immunefi", "description": "Immunefi — bug bounties, vulnerability reports.", "reliability_score": 92},
    {"name": "Rekt News", "type": "rss", "url": "https://rekt.news/feed.xml", "description": "Rekt — DeFi exploit analysis, postmortems.", "reliability_score": 90},

    # ════════════════════════════════════════════════════════
    # WIRE SERVICES & MAINSTREAM FINANCE (Crypto filtered)
    # ════════════════════════════════════════════════════════
    {"name": "Reuters Crypto", "type": "rss", "url": "https://news.google.com/rss/search?q=cryptocurrency+OR+bitcoin+OR+ethereum+site:reuters.com&hl=en-US&gl=US&ceid=US:en", "description": "Reuters — original crypto wire reporting.", "reliability_score": 96},
    {"name": "Bloomberg Crypto", "type": "rss", "url": "https://news.google.com/rss/search?q=cryptocurrency+OR+bitcoin+OR+blockchain+site:bloomberg.com&hl=en-US&gl=US&ceid=US:en", "description": "Bloomberg — financial market crypto coverage.", "reliability_score": 95},
    {"name": "AP News Crypto", "type": "rss", "url": "https://news.google.com/rss/search?q=cryptocurrency+OR+bitcoin+OR+blockchain+site:apnews.com&hl=en-US&gl=US&ceid=US:en", "description": "Associated Press — trusted wire crypto reporting.", "reliability_score": 97},
    {"name": "CNBC Crypto", "type": "rss", "url": "https://news.google.com/rss/search?q=crypto+OR+bitcoin+site:cnbc.com&hl=en-US&gl=US&ceid=US:en", "description": "CNBC — mainstream financial crypto coverage.", "reliability_score": 90},
    {"name": "Forbes Crypto", "type": "rss", "url": "https://news.google.com/rss/search?q=cryptocurrency+OR+bitcoin+site:forbes.com&hl=en-US&gl=US&ceid=US:en", "description": "Forbes — business and crypto reporting.", "reliability_score": 88},
    {"name": "WSJ Crypto", "type": "rss", "url": "https://news.google.com/rss/search?q=crypto+OR+bitcoin+OR+blockchain+site:wsj.com&hl=en-US&gl=US&ceid=US:en", "description": "Wall Street Journal — financial crypto analysis.", "reliability_score": 95},
    {"name": "Financial Times Crypto", "type": "rss", "url": "https://news.google.com/rss/search?q=cryptocurrency+OR+bitcoin+site:ft.com&hl=en-US&gl=US&ceid=US:en", "description": "Financial Times — global crypto financial reporting.", "reliability_score": 94},
    {"name": "NYT Crypto", "type": "rss", "url": "https://news.google.com/rss/search?q=cryptocurrency+OR+bitcoin+site:nytimes.com&hl=en-US&gl=US&ceid=US:en", "description": "New York Times — investigative crypto journalism.", "reliability_score": 93},

    # ════════════════════════════════════════════════════════
    # TECH PUBLICATIONS (Crypto coverage)
    # ════════════════════════════════════════════════════════
    {"name": "TechCrunch Crypto", "type": "rss", "url": "https://news.google.com/rss/search?q=crypto+OR+web3+OR+blockchain+site:techcrunch.com&hl=en-US&gl=US&ceid=US:en", "description": "TechCrunch — crypto startup and funding coverage.", "reliability_score": 89},
    {"name": "Wired Crypto", "type": "rss", "url": "https://news.google.com/rss/search?q=cryptocurrency+OR+blockchain+site:wired.com&hl=en-US&gl=US&ceid=US:en", "description": "Wired — technology and crypto deep dives.", "reliability_score": 88},
    {"name": "The Verge Crypto", "type": "rss", "url": "https://news.google.com/rss/search?q=crypto+OR+bitcoin+OR+web3+site:theverge.com&hl=en-US&gl=US&ceid=US:en", "description": "The Verge — tech and crypto news.", "reliability_score": 87},
    {"name": "Ars Technica Crypto", "type": "rss", "url": "https://news.google.com/rss/search?q=cryptocurrency+OR+blockchain+site:arstechnica.com&hl=en-US&gl=US&ceid=US:en", "description": "Ars Technica — technical crypto analysis.", "reliability_score": 89},

    # ════════════════════════════════════════════════════════
    # VENTURE CAPITAL & INVESTMENT RESEARCH
    # ════════════════════════════════════════════════════════
    {"name": "a16z Crypto Blog", "type": "rss", "url": "https://a16zcrypto.com/posts/rss", "description": "Andreessen Horowitz — crypto investment thesis, research.", "reliability_score": 92},
    {"name": "Paradigm Research", "type": "rss", "url": "https://www.paradigm.xyz/feed.xml", "description": "Paradigm — DeFi research, mechanism design.", "reliability_score": 93},
    {"name": "Electric Capital Blog", "type": "rss", "url": "https://medium.com/feed/electric-capital", "description": "Electric Capital — developer reports, ecosystem analysis.", "reliability_score": 91},
    {"name": "Pantera Capital Blog", "type": "rss", "url": "https://panteracapital.com/rss/", "description": "Pantera — blockchain fund letters, market outlook.", "reliability_score": 90},
    {"name": "Grayscale Research", "type": "rss", "url": "https://www.grayscale.com/research/rss", "description": "Grayscale — crypto asset management insights.", "reliability_score": 92},

    # ════════════════════════════════════════════════════════
    # INFRASTRUCTURE & DEVELOPER TOOLS
    # ════════════════════════════════════════════════════════
    {"name": "Alchemy Blog", "type": "rss", "url": "https://www.alchemy.com/blog/rss", "description": "Alchemy — web3 infrastructure, developer tools.", "reliability_score": 89},
    {"name": "Infura Blog", "type": "rss", "url": "https://blog.infura.io/feed", "description": "Infura — Ethereum node infrastructure.", "reliability_score": 90},
    {"name": "Etherscan Blog", "type": "rss", "url": "https://medium.com/feed/etherscan-blog", "description": "Etherscan — block explorer updates, tools.", "reliability_score": 91},
    {"name": "The Graph Blog", "type": "rss", "url": "https://thegraph.com/blog/rss.xml", "description": "The Graph — indexing protocol, subgraphs.", "reliability_score": 89},

    # ════════════════════════════════════════════════════════
    # NFT & GAMING
    # ════════════════════════════════════════════════════════
    {"name": "OpenSea Blog", "type": "rss", "url": "https://opensea.io/blog/feed", "description": "OpenSea — NFT marketplace updates.", "reliability_score": 87},
    {"name": "Immutable Blog", "type": "rss", "url": "https://www.immutable.com/blog/rss", "description": "Immutable — Web3 gaming, NFTs.", "reliability_score": 88},

    # ════════════════════════════════════════════════════════
    # STABLECOIN & PAYMENTS
    # ════════════════════════════════════════════════════════
    {"name": "Stripe Crypto Blog", "type": "rss", "url": "https://news.google.com/rss/search?q=crypto+OR+stablecoin+site:stripe.com&hl=en-US&gl=US&ceid=US:en", "description": "Stripe — crypto payment integration.", "reliability_score": 91},
    {"name": "PayPal Crypto News", "type": "rss", "url": "https://news.google.com/rss/search?q=crypto+OR+bitcoin+OR+PYUSD+site:paypal.com&hl=en-US&gl=US&ceid=US:en", "description": "PayPal — PYUSD, crypto payments.", "reliability_score": 90},
    {"name": "Visa Crypto", "type": "rss", "url": "https://news.google.com/rss/search?q=crypto+OR+blockchain+OR+stablecoin+site:visa.com&hl=en-US&gl=US&ceid=US:en", "description": "Visa — crypto settlement, stablecoin adoption.", "reliability_score": 93},

    # ════════════════════════════════════════════════════════
    # GITHUB RELEASES (Technical protocol updates)
    # ════════════════════════════════════════════════════════
    {"name": "Bitcoin Core Releases", "type": "rss", "url": "https://github.com/bitcoin/bitcoin/releases.atom", "description": "Official Bitcoin Core software releases.", "reliability_score": 99},
    {"name": "Go-Ethereum Releases", "type": "rss", "url": "https://github.com/ethereum/go-ethereum/releases.atom", "description": "Geth — Ethereum client releases.", "reliability_score": 99},
    {"name": "Solana Releases", "type": "rss", "url": "https://github.com/solana-labs/solana/releases.atom", "description": "Solana validator client releases.", "reliability_score": 98},
    {"name": "Prysm Releases", "type": "rss", "url": "https://github.com/prysmaticlabs/prysm/releases.atom", "description": "Prysm — Ethereum consensus client.", "reliability_score": 98},

    # ════════════════════════════════════════════════════════
    # GOOGLE NEWS AGGREGATED (catches everything else)
    # ════════════════════════════════════════════════════════
    {"name": "Google News: Bitcoin", "type": "rss", "url": "https://news.google.com/rss/search?q=bitcoin+price+OR+bitcoin+etf+OR+bitcoin+halving&hl=en-US&gl=US&ceid=US:en", "description": "Google News — Bitcoin focused stories.", "reliability_score": 80},
    {"name": "Google News: Ethereum", "type": "rss", "url": "https://news.google.com/rss/search?q=ethereum+OR+ETH+defi+OR+ethereum+upgrade&hl=en-US&gl=US&ceid=US:en", "description": "Google News — Ethereum focused stories.", "reliability_score": 80},
    {"name": "Google News: DeFi", "type": "rss", "url": "https://news.google.com/rss/search?q=defi+OR+decentralized+finance+OR+yield+farming&hl=en-US&gl=US&ceid=US:en", "description": "Google News — DeFi focused stories.", "reliability_score": 78},
    {"name": "Google News: Crypto Regulation", "type": "rss", "url": "https://news.google.com/rss/search?q=crypto+regulation+OR+SEC+crypto+OR+crypto+law&hl=en-US&gl=US&ceid=US:en", "description": "Google News — Crypto regulation stories.", "reliability_score": 82},
    {"name": "Google News: NFT", "type": "rss", "url": "https://news.google.com/rss/search?q=NFT+OR+non-fungible+token+marketplace&hl=en-US&gl=US&ceid=US:en", "description": "Google News — NFT stories.", "reliability_score": 75},
    {"name": "Google News: Crypto Security", "type": "rss", "url": "https://news.google.com/rss/search?q=crypto+hack+OR+crypto+scam+OR+crypto+exploit&hl=en-US&gl=US&ceid=US:en", "description": "Google News — Crypto security incidents.", "reliability_score": 80},
]
