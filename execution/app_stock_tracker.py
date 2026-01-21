import streamlit as st
import yfinance as yf
import pandas as pd
import os
import google.generativeai as genai
from dotenv import load_dotenv

# Load Environment Variables
load_dotenv()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)

# Constants
PORTFOLIO_FILE = "portfolio.csv"

# --- Data Persistence Functions ---
def load_portfolio():
    if os.path.exists(PORTFOLIO_FILE):
        return pd.read_csv(PORTFOLIO_FILE)
    else:
        return pd.DataFrame(columns=["Ticker", "PMC", "Quantity"])

def save_portfolio(df):
    df.to_csv(PORTFOLIO_FILE, index=False)

def add_asset(ticker, pmc, qty):
    df = load_portfolio()
    
    # Normalize input
    ticker = ticker.strip().upper()
    
    # Ensure Ticker column is string and normalized (just in case)
    if not df.empty:
        df['Ticker'] = df['Ticker'].astype(str).str.strip().str.upper()

    # Check if ticker exists
    if ticker in df['Ticker'].values:
        df.loc[df['Ticker'] == ticker, 'PMC'] = pmc
        df.loc[df['Ticker'] == ticker, 'Quantity'] = qty
    else:
        new_row = pd.DataFrame({"Ticker": [ticker], "PMC": [pmc], "Quantity": [qty]})
        df = pd.concat([df, new_row], ignore_index=True)
    save_portfolio(df)

def remove_asset(ticker):
    df = load_portfolio()
    df = df[df['Ticker'] != ticker]
    save_portfolio(df)

# --- Fetch Data Helper ---
def get_current_data(ticker):
    try:
        stock = yf.Ticker(ticker)
        # Fast info
        info = stock.info
        price = info.get('currentPrice') or info.get('regularMarketPrice') or info.get('price')
        
        # Daily Change
        change_pct = info.get('regularMarketChangePercent')
        if change_pct is None and price:
             previous_close = info.get('previousClose') or info.get('regularMarketPreviousClose')
             if previous_close:
                 change_pct = ((price - previous_close) / previous_close) * 100
        
        # Name and Type
        name = info.get('longName') or info.get('shortName') or ticker
        q_type = info.get('quoteType', 'N/A')
        
        # Fallback to history if info fails
        if not price:
            hist = stock.history(period="1d")
            if not hist.empty:
                price = hist['Close'].iloc[-1]
                # Try to calculate change from history if not available (approximate)
                if change_pct is None:
                     # This is trickier with just 1d history, usually need 2d to get prev close
                     # For now, let's try to fetch 2 days if we are falling back
                     hist_2d = stock.history(period="5d") # Fetching a bit more to be safe
                     if len(hist_2d) >= 2:
                         prev_close = hist_2d['Close'].iloc[-2]
                         change_pct = ((price - prev_close) / prev_close) * 100
            else:
                return None, None, None, None
        
        # Ensure change_pct is not None for display (default to 0.0 if missing)
        if change_pct is None:
            change_pct = 0.0

        return price, change_pct, name, q_type
    except:
        return None, None, None, None

# --- AI Helper ---
def ask_gemini(prompt):
    if not GEMINI_API_KEY:
        return "⚠️ API Key mancante. Inserisci GEMINI_API_KEY nel file .env"
    try:
        model = genai.GenerativeModel('gemini-2.0-flash')
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        return f"Errore AI: {e}"

# --- Views ---

def render_dashboard(portfolio_df):
    st.header("📊 VISTA GENERALE PORTAFOGLIO")
    
    if portfolio_df.empty:
        st.info("Il portafoglio è vuoto. Aggiungi titoli dalla barra laterale.")
        return

    # Calculate Totals
    total_invested = 0.0
    total_value = 0.0
    
    portfolio_data = []

    progress_bar = st.progress(0)
    for i, row in portfolio_df.iterrows():
        ticker = row['Ticker']
        qty = row['Quantity']
        pmc = row['PMC']
        
        current_price, change_pct, name, q_type = get_current_data(ticker)
        
        progress_bar.progress((i + 1) / len(portfolio_df))
        
        if current_price is None:
            st.warning(f"Impossibile recuperare dati per {ticker}")
            continue

        invested = pmc * qty
        value = current_price * qty
        pl_val = value - invested
        pl_pct = (pl_val / invested) * 100 if invested > 0 else 0

        total_invested += invested
        total_value += value
        
        # Translate Type
        type_map = {"EQUITY": "Azione", "ETF": "ETF", "MUTUALFUND": "Fondo"}
        display_type = type_map.get(q_type, q_type)

        portfolio_data.append({
            "Ticker": ticker,
            "Nome": name,
            "Tipo": display_type,
            "Prezzo": current_price,
            "Var % 1d": change_pct,
            "PMC": pmc,
            "Quantità": qty,
            "Valore": value,
            "P/L €": pl_val,
            "P/L %": pl_pct
        })
    
    progress_bar.empty()

    # Total Metrics
    total_pl = total_value - total_invested
    total_pl_pct = (total_pl / total_invested) * 100 if total_invested > 0 else 0

    c1, c2, c3 = st.columns(3)
    c1.metric("Valore Totale", f"{total_value:,.2f} €")
    c1.caption(f"Investito: {total_invested:,.2f} €")
    c2.metric("Profitto/Perdita Totale", f"{total_pl:,.2f} €", f"{total_pl_pct:+.2f}%")
    
    # AI Analysis Button
    if st.button("🤖 Analisi Portafoglio AI"):
        with st.spinner("L'AI sta analizzando il tuo portafoglio..."):
            prompt = f"""
            Sei un esperto gestore di portafoglio. Analizza brevemente questo portafoglio:
            - Valore Totale: {total_value:.2f} €
            - Profitto/Perdita Totale: {total_pl:.2f} € ({total_pl_pct:.2f}%)
            - Composizione: {portfolio_data}
            
            Fornisci un commento sulla diversificazione, i rischi principali e un consiglio sintetico. Usa markdown e sii conciso (max 5 righe).
            """
            analysis = ask_gemini(prompt)
            st.info(analysis)

    # Data Table
    st.subheader("Dettaglio Asset")
    df_display = pd.DataFrame(portfolio_data)
    if not df_display.empty:
        # Style function
        def color_pl(val):
            color = 'green' if val >= 0 else 'red'
            return f'color: {color}'

        # Format for nicer display
        st.dataframe(df_display.style.format({
            "Prezzo": "{:.4f}",
            "Var % 1d": "{:+.2f}%",
            "PMC": "{:.4f}",
            "Valore": "{:.2f}",
            "P/L €": "{:+.2f}",
            "P/L %": "{:+.2f}%"
        }).map(color_pl, subset=["P/L €", "P/L %", "Var % 1d"]))

    # Pie Chart
    st.subheader("Allocazione Asset")
    if not df_display.empty:
        st.bar_chart(df_display.set_index("Ticker")["Valore"])


def render_stock_detail(ticker, pmc, quantity):
    st.header(f"📈 Analisi Titolo: {ticker}")
    
    # Inputs for analysis
    c1, c2 = st.columns([1, 1])
    with c1:
        period = st.selectbox("Periodo Grafico", ("1mo", "3mo", "6mo", "1y", "2y", "5y", "max"), index=3)
    
    try:
        stock = yf.Ticker(ticker)
        hist = stock.history(period=period)
        
        if hist.empty:
            st.error(f"Nessun dato trovato per {ticker}.")
            return

        info = stock.info
        current_price = info.get('currentPrice') or info.get('regularMarketPrice') or hist['Close'].iloc[-1]
        currency = info.get('currency', 'EUR')
        stock_name = info.get('longName') or info.get('shortName') or ticker

        # --- Metrics & P/L ---
        st.subheader(f"{stock_name} ({ticker})")
        col_price, col_pl = st.columns(2)
        col_price.metric(label=f"Prezzo Attuale", value=f"{current_price:.4f} {currency}")

        if pmc > 0 and quantity > 0:
            pl_value = (current_price - pmc) * quantity
            pl_percent = ((current_price - pmc) / pmc) * 100
            col_pl.metric("Profitto/Perdita (su Posseduto)", 
                          f"{pl_value:+.2f} {currency}", 
                          f"{pl_percent:+.2f}%", 
                          delta_color="normal")
            st.caption(f"Possiedi **{quantity}** azioni con PMC **{pmc}**")

        # --- Technical Analysis Calculations ---
        hist['SMA_20'] = hist['Close'].rolling(window=20).mean()
        hist['SMA_50'] = hist['Close'].rolling(window=50).mean()
        
        delta = hist['Close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        hist['RSI'] = 100 - (100 / (1 + (gain / loss)))

        # --- Display Signal Section (Moved Up) ---
        st.subheader("💡 Analisi Tecnica & Segnali")
        last_close = hist['Close'].iloc[-1]
        last_sma20 = hist['SMA_20'].iloc[-1]
        last_sma50 = hist['SMA_50'].iloc[-1]
        last_rsi = hist['RSI'].iloc[-1]

        signal = "HOLD"
        reason = "Nessun segnale forte."
        
        if (last_close > last_sma20 and last_close > last_sma50):
            signal = "BUY"
            reason = "Trend Rialzista (Prezzo > SMA20/50)."
        elif last_rsi < 30:
            signal = "BUY"
            reason = "Ipervenduto (RSI < 30)."
        elif last_close < last_sma50:
            signal = "SELL"
            reason = "Trend Ribassista (Prezzo < SMA50)."
        elif last_rsi > 70:
            signal = "SELL"
            reason = "Ipercomprato (RSI > 70)."

        if signal == "BUY": st.success(f"**{signal}**: {reason}")
        elif signal == "SELL": st.error(f"**{signal}**: {reason}")
        else: st.warning(f"**{signal}**: {reason}")

        # AI Button
        if st.button(f"🤖 Chiedi Analisi AI su {ticker}"):
            with st.spinner(f"L'AI sta analizzando i dati tecnici di {ticker}..."):
                prompt = f"""
                Sei un analista tecnico finanziario. Analizza i seguenti dati per l'azione {ticker} ({stock_name}):
                - Prezzo Attuale: {current_price}
                - SMA 20: {last_sma20}
                - SMA 50: {last_sma50}
                - RSI (14): {last_rsi}
                - Segnale Algoritmico Rilevato: {signal} ({reason})
                
                Fornisci una brevissima analisi (3 punti elenco) sulla situazione tecnica e conferma o smentisci il segnale algoritmico.
                """
                ai_response = ask_gemini(prompt)
                st.info(ai_response)

        sl_price = last_close * 0.97
        tp_price = last_close * 1.06
        k1, k2, k3 = st.columns(3)
        k1.metric("Prezzo", f"{last_close:.4f}")
        k2.metric("Stop Loss (-3%)", f"{sl_price:.4f}", delta="-3%", delta_color="inverse")
        k3.metric("Take Profit (+6%)", f"{tp_price:.4f}", delta="+6%")

        # --- Charts ---
        st.subheader(f"Grafico Prezzo ({period})")
        chart_data = hist[['Close', 'SMA_20', 'SMA_50']].copy()
        if pmc > 0:
            chart_data['Load Price'] = pmc
        st.line_chart(chart_data)

        st.subheader("RSI")
        st.line_chart(hist['RSI'])

    except Exception as e:
        st.error(f"Errore: {e}")

# --- Main App Orchestrator ---
def main():
    st.set_page_config(page_title="Portfolio Manager", page_icon="💼", layout="wide")
    
    # Load Data
    portfolio = load_portfolio()

    # --- SIDEBAR ---
    st.sidebar.title("💼 Portafoglio")
    
    # Navigation
    nav_options = ["VISTA GENERALE"] + portfolio['Ticker'].tolist()
    selection = st.sidebar.radio("Navigazione", nav_options)

    st.sidebar.markdown("---")
    
    # Edit Portfolio Form
    with st.sidebar.expander("➕ Gestisci Titoli"):
        with st.form("add_asset_form"):
            new_ticker = st.text_input("Ticker (es. TIT.MI)")
            new_pmc = st.number_input("Prezzo Medio Carico", min_value=0.0, step=0.01, format="%.4f")
            new_qty = st.number_input("Quantità", min_value=1, step=1)
            submitted = st.form_submit_button("Aggiungi / Aggiorna")
            if submitted and new_ticker:
                add_asset(new_ticker, new_pmc, new_qty)
                st.success(f"Salvato {new_ticker}")
                st.rerun()
        
        st.write("---")
        with st.form("remove_asset_form"):
            rem_ticker = st.selectbox("Rimuovi Titolo", portfolio['Ticker'].unique())
            rem_submitted = st.form_submit_button("Rimuovi")
            if rem_submitted:
                remove_asset(rem_ticker)
                st.warning(f"Rimosso {rem_ticker}")
                st.rerun()

    # --- MAIN CONTENT ---
    if selection == "VISTA GENERALE":
        render_dashboard(portfolio)
    else:
        # Get data for selected ticker
        row = portfolio[portfolio['Ticker'] == selection].iloc[0]
        render_stock_detail(row['Ticker'], row['PMC'], row['Quantity'])

if __name__ == "__main__":
    main()
