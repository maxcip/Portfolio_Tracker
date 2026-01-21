import yfinance as yf
import sys

print(f"Python version: {sys.version}")
print(f"yfinance version: {yf.__version__}")

tickers = ["AAPL", "TIT.MI"]

for t in tickers:
    print(f"\nTesting {t}...")
    try:
        dat = yf.Ticker(t)
        hist = dat.history(period="1mo")
        if hist.empty:
            print(f"FAILURE: No data for {t}")
        else:
            print(f"SUCCESS: Got {len(hist)} rows for {t}")
            print(hist.head(2))
    except Exception as e:
        print(f"CRASH: {e}")
