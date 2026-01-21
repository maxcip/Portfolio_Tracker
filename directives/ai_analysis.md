# AI Analysis

## Goal
Provide qualitative financial analysis using Google Gemini AI.

## Configuration
- **API Key**: Must be available in environment variable `GEMINI_API_KEY`.
- **Model**: `gemini-1.5-flash` (fast and cost-effective) or `gemini-pro`.

## Prompts

### Single Stock Analysis
**Context**: You are a financial analyst aid.
**Input**:
- Ticker: {ticker}
- Current Price: {price}
- Technical Indicators: RSI={rsi}, SMA20={sma20}, SMA50={sma50}
- Trend Signal: {signal}
**Task**: Provide a concise 3-bullet point summary on the technical outlook. Be extremely brief.

### Portfolio Analysis
**Context**: You are a portfolio manager aid.
**Input**:
- Total Value: {total_value}
- Total P/L: {total_pl} ({total_pl_pct}%)
- Assets: {list_of_assets}
**Task**: Comment on the diversification and overall performance. risk assessment. Max 3 sentences.
