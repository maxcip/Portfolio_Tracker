# Manage Portfolio

## Goal
Manage a portfolio of assets (Ticker, Average Load Price, Quantity) and visualize aggregate performance.

## Data Storage
- `portfolio.csv`: Stores the portfolio state.
- Columns: `Ticker`, `PMC` (Prezzo Medio Carico), `Quantity`.
- Location: Same directory as execution script or project root.

## Interface
### Sidebar
- **Navigation**: Choice between "VISTA GENERALE" (Dashboard) and individual tickers present in the portfolio.
- **Edit Portfolio**: Form to Add new Ticker (Symbol, PMC, Qty) or Remove existing ones.

### Dashboard (Main View)
- Total Portfolio Value (Sum of Current Price * Qty).
- Total Profit/Loss (Value and Percentage).
- Asset Allocation (Pie Chart of value per ticker).
- Table summary of all assets with their daily change and total gain/loss.

### Stock Detail (Main View)
- Reuses the `track_stock_price` logic but auto-fills `Ticker` and `PMC` from the selected portfolio item.
- Shows specific Technical Analysis and Signals for the selected asset.
