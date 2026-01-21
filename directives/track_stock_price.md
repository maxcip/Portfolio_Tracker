# Track Stock Price

## Goal
Visualize the stock price and history for a given ticker symbol (default: TIT.MI).

## Inputs
- Ticker symbol (optional, default: "TIT.MI")
- Average Load Price (optional)

## Tools
- Python
- `streamlit`: For the web interface
- `yfinance`: For fetching stock data

## Procedure
1.  Fetch historical data for the ticker using `yfinance`.
2.  Display the current market price.
3.  Calculate Profit/Loss if Load Price is provided.
4.  Display a line chart associated with historical closing prices.
5.  Allow user to select time period (1mo, 3mo, 6mo, 1y, etc.).

## Output
- A Streamlit web application running locally.
- Stock price visualization (Line Chart).
- Technical Indicators (SMA 20/50, RSI 14).
- Trading Signals (Buy/Sell/Hold).
- Key Levels (Stop Loss, Take Profit).
- Portfolio Performance (Profit/Loss).
