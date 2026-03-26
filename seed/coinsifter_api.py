"""
CoinSifter API — Seed listing for Agent Commerce marketplace.
Wraps CoinSifter crypto scanning as a paid API service.

This module can run standalone (FastAPI server) or be registered
as a service on the marketplace.
"""
from __future__ import annotations

import os
import sys
import logging
from datetime import datetime, timezone
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import JSONResponse

# Add CoinSifter to path if available
COINSIFTER_PATH = Path(os.environ.get(
    "COINSIFTER_PATH",
    str(Path(__file__).parent.parent.parent / "coinsifter")
))

logger = logging.getLogger("coinsifter-api")

app = FastAPI(
    title="CoinSifter API",
    description="Crypto market scanning & technical analysis API",
    version="1.0.0",
)


def _get_scanner():
    """Lazy-load CoinSifter scanner."""
    if str(COINSIFTER_PATH) not in sys.path:
        sys.path.insert(0, str(COINSIFTER_PATH))
    try:
        from core.scanner import create_exchange, scan_all_usdt
        return create_exchange(), scan_all_usdt
    except ImportError:
        logger.warning("CoinSifter not found at %s", COINSIFTER_PATH)
        return None, None


def _get_filter_engine():
    """Lazy-load CoinSifter filter engine."""
    if str(COINSIFTER_PATH) not in sys.path:
        sys.path.insert(0, str(COINSIFTER_PATH))
    try:
        from core.filter_engine import run_filters
        return run_filters
    except ImportError:
        return None


# --- Free endpoints ---

@app.get("/")
async def root():
    return {
        "service": "CoinSifter API",
        "version": "1.0.0",
        "endpoints": {
            "/api/scan": {
                "price": "$0.01",
                "method": "GET",
                "description": "Scan top crypto pairs by volume/change",
            },
            "/api/signals": {
                "price": "$0.02",
                "method": "GET",
                "description": "Get filtered trading signals",
            },
            "/api/report/{symbol}": {
                "price": "$0.05",
                "method": "GET",
                "description": "Detailed analysis for a specific coin",
            },
        },
        "payment": {"protocol": "x402", "currency": "USDC"},
    }


@app.get("/health")
async def health():
    exchange, _ = _get_scanner()
    return {
        "status": "ok" if exchange else "degraded",
        "coinsifter_available": exchange is not None,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


# --- Paid endpoints ---

@app.get("/api/scan")
async def scan(
    sort_by: str = Query("volume", enum=["volume", "gainers", "losers"]),
    top_n: int = Query(20, ge=1, le=100),
    min_volume: float = Query(50_000_000, ge=0),
):
    """Scan top crypto pairs. Returns sorted list with price and volume data."""
    exchange, scan_fn = _get_scanner()
    if not exchange or not scan_fn:
        raise HTTPException(
            status_code=503,
            detail="CoinSifter scanner not available"
        )

    try:
        df = scan_fn(
            exchange,
            min_volume=min_volume,
            top_n=top_n,
            sort_by=sort_by,
        )

        results = []
        for _, row in df.iterrows():
            results.append({
                "symbol": row.get("symbol", ""),
                "base": row.get("base", ""),
                "price": round(float(row.get("price", 0)), 8),
                "volume_24h": round(float(row.get("volume_24h", 0)), 2),
                "change_pct": round(float(row.get("change_pct", 0)), 2),
            })

        return {
            "data": results,
            "count": len(results),
            "sort_by": sort_by,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    except Exception as e:
        logger.error("Scan error: %s", e)
        raise HTTPException(status_code=500, detail="Scan failed")


@app.get("/api/signals")
async def signals(
    strategy: str = Query("trend_long", enum=["trend_long", "trend_short"]),
    top_n: int = Query(10, ge=1, le=50),
):
    """Get filtered trading signals based on strategy."""
    exchange, scan_fn = _get_scanner()
    run_filters = _get_filter_engine()

    if not exchange or not scan_fn or not run_filters:
        raise HTTPException(
            status_code=503,
            detail="CoinSifter engine not available"
        )

    try:
        # Load strategy config
        strategy_path = COINSIFTER_PATH / "strategies" / f"{strategy}.yaml"
        if not strategy_path.exists():
            raise HTTPException(
                status_code=400,
                detail=f"Strategy '{strategy}' not found"
            )

        import yaml
        with open(strategy_path) as f:
            config = yaml.safe_load(f)

        # Scan + Filter
        df = scan_fn(exchange, top_n=100)
        filtered = run_filters(df, config, exchange)

        results = []
        for _, row in filtered.head(top_n).iterrows():
            results.append({
                "symbol": row.get("symbol", ""),
                "signal": strategy.replace("_", " ").title(),
                "price": round(float(row.get("price", 0)), 8),
                "score": round(float(row.get("score", 0)), 2)
                if "score" in row else None,
            })

        return {
            "data": results,
            "strategy": strategy,
            "count": len(results),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Signal error: %s", e)
        raise HTTPException(status_code=500, detail="Signal generation failed")


@app.get("/api/report/{symbol}")
async def report(symbol: str):
    """Detailed technical analysis report for a specific symbol."""
    exchange, _ = _get_scanner()
    if not exchange:
        raise HTTPException(
            status_code=503,
            detail="Exchange connection not available"
        )

    # Normalize symbol
    if "/" not in symbol:
        symbol = f"{symbol.upper()}/USDT"

    try:
        # Fetch OHLCV data
        ohlcv = exchange.fetch_ohlcv(symbol, "1d", limit=90)
        if not ohlcv:
            raise HTTPException(
                status_code=404,
                detail=f"No data for {symbol}"
            )

        ticker = exchange.fetch_ticker(symbol)

        # Basic analysis
        closes = [c[4] for c in ohlcv]
        current = closes[-1]
        sma_20 = sum(closes[-20:]) / 20 if len(closes) >= 20 else current
        sma_50 = sum(closes[-50:]) / 50 if len(closes) >= 50 else current

        high_90d = max(closes)
        low_90d = min(closes)
        avg_volume = sum(c[5] for c in ohlcv[-20:]) / 20

        return {
            "symbol": symbol,
            "price": round(current, 8),
            "change_24h": round(float(ticker.get("percentage", 0) or 0), 2),
            "volume_24h": round(float(ticker.get("quoteVolume", 0) or 0), 2),
            "technical": {
                "sma_20": round(sma_20, 8),
                "sma_50": round(sma_50, 8),
                "trend": "bullish" if current > sma_20 > sma_50 else
                         "bearish" if current < sma_20 < sma_50 else "neutral",
                "high_90d": round(high_90d, 8),
                "low_90d": round(low_90d, 8),
                "distance_from_high": round(
                    (current - high_90d) / high_90d * 100, 2
                ),
            },
            "volume": {
                "avg_20d": round(avg_volume, 2),
                "current_vs_avg": round(
                    float(ticker.get("quoteVolume", 0) or 0) / avg_volume * 100
                    if avg_volume > 0 else 0, 1
                ),
            },
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Report error for %s: %s", symbol, e)
        raise HTTPException(status_code=500, detail="Report generation failed")


# --- Marketplace registration helper ---

def get_marketplace_listing() -> dict:
    """Return marketplace listing metadata for registration."""
    return {
        "name": "CoinSifter Crypto Scanner API",
        "description": (
            "Real-time crypto market scanning, technical analysis signals, "
            "and per-coin reports. Covers 100+ USDT pairs on Binance. "
            "Strategies: trend_long, trend_short."
        ),
        "category": "data",
        "tags": ["crypto", "trading", "technical-analysis", "market-data"],
        "endpoints": [
            {"path": "/api/scan", "price": "0.01", "method": "GET"},
            {"path": "/api/signals", "price": "0.02", "method": "GET"},
            {"path": "/api/report/{symbol}", "price": "0.05", "method": "GET"},
        ],
    }
