"""
Seed demo news articles for testing the API without real scraping.
Usage: python manage.py seed_demo
"""

from django.core.management.base import BaseCommand
from django.utils import timezone
from news.models import Source, NewsArticle, VerificationLog


DEMO_ARTICLES = [
    {
        "title": "Bitcoin Surges Past $105K as Institutional Adoption Accelerates",
        "summary": "Bitcoin reached a new all-time high above $105,000 as major financial institutions increase their crypto holdings.",
        "content": "<p>Bitcoin has surged past the $105,000 mark for the first time in history, driven by a wave of institutional adoption. The rally has been primarily fueled by record inflows into spot Bitcoin ETFs, which collectively absorbed over $2.8 billion in the past five trading days.</p><p>BlackRock's iShares Bitcoin Trust (IBIT) alone accounted for $1.2 billion of those inflows. On-chain data supports the bullish narrative, with exchange reserves continuing to decline.</p>",
        "ai_verdict": "REAL",
        "confidence_score": 94,
        "category": "Markets",
        "tags": ["Bitcoin", "ETF", "Institutional"],
        "author": "Michael Chen",
        "images": [
            "https://images.unsplash.com/photo-1518546305927-5a555bb7020d?w=800&q=80",
            "https://images.unsplash.com/photo-1611974789855-9c2a0a7236a3?w=800&q=80",
            "https://images.unsplash.com/photo-1642790106117-e829e14a795f?w=800&q=80",
        ],
        "is_breaking": True,
    },
    {
        "title": "Ethereum Layer 2 Networks Process More Transactions Than Mainnet",
        "summary": "Combined L2 throughput now exceeds Ethereum mainnet by 5x, with Arbitrum and Base leading.",
        "content": "<p>Ethereum's Layer 2 scaling ecosystem has reached a historic milestone: combined transaction throughput now surpasses the Ethereum mainnet by a factor of five. According to L2Beat, total TPS across all L2s averaged 487 TPS over the past week.</p>",
        "ai_verdict": "REAL",
        "confidence_score": 91,
        "category": "Technology",
        "tags": ["Ethereum", "Layer 2", "Scaling"],
        "author": "Sarah Kim",
        "images": [
            "https://images.unsplash.com/photo-1639762681485-074b7f938ba0?w=800&q=80",
            "https://images.unsplash.com/photo-1622630998477-20aa696ecb05?w=800&q=80",
        ],
    },
    {
        "title": "SEC Approves First Solana Spot ETF in Landmark Decision",
        "summary": "The SEC has greenlit the first Solana spot ETF, opening the door for mainstream investment.",
        "content": "<p>The U.S. SEC has approved the first spot Solana exchange-traded fund. The VanEck Solana Trust will begin trading under the ticker 'VSOL' starting next week. Solana's price jumped 18% to $285 within hours of the announcement.</p>",
        "ai_verdict": "UNCERTAIN",
        "confidence_score": 67,
        "category": "Regulation",
        "tags": ["Solana", "ETF", "SEC"],
        "author": "James Rodriguez",
        "images": [
            "https://images.unsplash.com/photo-1640340434855-6084b1f4901c?w=800&q=80",
            "https://images.unsplash.com/photo-1621504450181-5d356f61d307?w=800&q=80",
            "https://images.unsplash.com/photo-1620321023374-d1a68fbc720d?w=800&q=80",
        ],
    },
    {
        "title": "Fake Airdrop Scam Targets 200K Wallets in Sophisticated Attack",
        "summary": "Security researchers uncover a large-scale phishing campaign draining $15M from users.",
        "content": "<p>Blockchain security firm SlowMist has identified a massive phishing operation that impersonated a legitimate DeFi protocol's airdrop, targeting over 200,000 wallets and draining approximately $15 million.</p>",
        "ai_verdict": "REAL",
        "confidence_score": 88,
        "category": "Security",
        "tags": ["Scam", "Phishing", "Security"],
        "author": "Alex Torres",
        "images": [
            "https://images.unsplash.com/photo-1563013544-824ae1b704d3?w=800&q=80",
            "https://images.unsplash.com/photo-1550751827-4bd374c3f58b?w=800&q=80",
        ],
    },
    {
        "title": "Alleged Satoshi Nakamoto Identity Revealed — Experts Remain Skeptical",
        "summary": "A new documentary claims to reveal Bitcoin creator's true identity, but experts cast doubt.",
        "content": "<p>A documentary claims to have identified Satoshi Nakamoto. However, the crypto community responded with significant skepticism. The Bitcoin Foundation noted that the documentary fails to provide cryptographic proof.</p>",
        "ai_verdict": "FAKE",
        "confidence_score": 82,
        "category": "Culture",
        "tags": ["Satoshi", "Bitcoin", "Identity"],
        "author": "Tom Williams",
        "images": [
            "https://images.unsplash.com/photo-1516245834210-c4c142787335?w=800&q=80",
            "https://images.unsplash.com/photo-1621504450181-5d356f61d307?w=800&q=80",
        ],
    },
    {
        "title": "DeFi Protocol Aave Crosses $50B in Total Value Locked",
        "summary": "Aave becomes the first DeFi lending protocol to surpass $50 billion TVL.",
        "content": "<p>Aave has crossed the $50 billion TVL milestone. Institutional participation accounts for an estimated 35% of total deposits. The protocol's GHO stablecoin has a circulating supply exceeding $1.5 billion.</p>",
        "ai_verdict": "REAL",
        "confidence_score": 93,
        "category": "DeFi",
        "tags": ["Aave", "DeFi", "TVL"],
        "author": "Nina Patel",
        "images": [
            "https://images.unsplash.com/photo-1642790106117-e829e14a795f?w=800&q=80",
            "https://images.unsplash.com/photo-1646463535685-f0cf42cb3127?w=800&q=80",
        ],
        "is_breaking": True,
    },
    {
        "title": "MicroStrategy Now Holds 500,000 Bitcoin Worth $52 Billion",
        "summary": "Michael Saylor's company reaches half a million BTC after latest $4.2B purchase.",
        "content": "<p>MicroStrategy has completed its latest Bitcoin acquisition of 40,000 BTC for $4.2 billion, bringing total holdings to 500,000 BTC valued at roughly $52 billion. Average cost basis is approximately $43,000 per Bitcoin.</p>",
        "ai_verdict": "REAL",
        "confidence_score": 97,
        "category": "Markets",
        "tags": ["MicroStrategy", "Bitcoin", "Corporate"],
        "author": "David Park",
        "images": [
            "https://images.unsplash.com/photo-1611974789855-9c2a0a7236a3?w=800&q=80",
            "https://images.unsplash.com/photo-1518546305927-5a555bb7020d?w=800&q=80",
        ],
        "is_breaking": True,
    },
    {
        "title": "Central Bank of Brazil Launches Digital Real Pilot",
        "summary": "Brazil becomes the first G20 nation to pilot a CBDC with native DeFi integration.",
        "content": "<p>The Central Bank of Brazil has officially launched the pilot phase of its digital real (DREX), becoming the first G20 economy to integrate DeFi protocols directly into its CBDC infrastructure. The pilot will initially serve 50 million citizens.</p>",
        "ai_verdict": "REAL",
        "confidence_score": 96,
        "category": "CBDC",
        "tags": ["CBDC", "Brazil", "DeFi"],
        "author": "Maria Fernandez",
        "images": [
            "https://images.unsplash.com/photo-1551288049-bebda4e38f71?w=800&q=80",
            "https://images.unsplash.com/photo-1526304640581-d334cdbbf45e?w=800&q=80",
        ],
    },
    {
        "title": "NFT Market Rebounds: Daily Trading Volume Hits $120M",
        "summary": "NFT market recovers with daily volumes surpassing $120M, driven by gaming assets and RWA tokenization.",
        "content": "<p>After a prolonged downturn, the NFT market shows strong signs of recovery. Daily trading volume has surged to $120 million. Gaming assets account for 45% of volume, while real-world asset tokenization makes up another 30%.</p>",
        "ai_verdict": "REAL",
        "confidence_score": 85,
        "category": "NFT",
        "tags": ["NFT", "Gaming", "RWA"],
        "author": "Lisa Chang",
        "images": [
            "https://images.unsplash.com/photo-1646463535685-f0cf42cb3127?w=800&q=80",
            "https://images.unsplash.com/photo-1639762681485-074b7f938ba0?w=800&q=80",
        ],
    },
]


class Command(BaseCommand):
    help = "Seed demo news articles for testing the frontend."

    def handle(self, *args, **options):
        # Ensure at least one source exists
        source, _ = Source.objects.get_or_create(
            name="Demo Source",
            defaults={
                "type": "website",
                "url": "https://demo.cryptotimes.dev",
                "description": "Demo data source for development.",
                "reliability_score": 90,
            },
        )

        created_count = 0
        for i, data in enumerate(DEMO_ARTICLES):
            is_breaking = data.pop("is_breaking", False)

            article, created = NewsArticle.objects.get_or_create(
                title=data["title"],
                defaults={
                    **data,
                    "source": source,
                    "status": "approved",
                    "is_breaking": is_breaking,
                    "published_at": timezone.now(),
                },
            )

            if created:
                # Create a verification log
                VerificationLog.objects.create(
                    article=article,
                    verdict=article.ai_verdict,
                    confidence_score=article.confidence_score,
                    explanation=f"Mock verification for demo article.",
                    provider="mock",
                    raw_response={"demo": True},
                )
                created_count += 1
                self.stdout.write(f"  + {data['title'][:60]}")
            else:
                self.stdout.write(f"  ○ {data['title'][:60]} (exists)")

        self.stdout.write(self.style.SUCCESS(f"\nDone — {created_count} demo articles created."))
