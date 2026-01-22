import streamlit as st
import yfinance as yf
import pandas as pd
import os
import time
import hashlib
from datetime import datetime
from groq import Groq
from dotenv import load_dotenv
from streamlit_cookies_manager import EncryptedCookieManager

# Load Environment Variables
load_dotenv()
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
APP_PASSWORD = os.getenv("APP_PASSWORD")

# Initialize Groq client
groq_client = None
if GROQ_API_KEY:
    groq_client = Groq(api_key=GROQ_API_KEY)

# Initialize cookies manager (persistent across page reloads)
cookies = EncryptedCookieManager(
    prefix="portfolio_app_",
    password="portfolio_secret_key_12345"  # Cookie encryption key
)

if not cookies.ready():
    st.stop()

# --- Authentication ---
def check_password():
    """Returns `True` if the user had the correct password. Uses cookies for persistence."""
    if not APP_PASSWORD:
        return True # No password set, allow access

    # Generate expected auth token
    expected_token = hashlib.sha256(APP_PASSWORD.encode()).hexdigest()
    
    # Check if already authenticated via cookie
    if cookies.get("auth_token") == expected_token:
        return True
    
    def password_entered():
        # Use .get() for safe access - prevents KeyError
        entered_password = st.session_state.get("password", "")
        
        if entered_password == APP_PASSWORD:
            st.session_state["password_correct"] = True
            # Save auth token in cookie (persists across page reloads)
            cookies["auth_token"] = expected_token
            cookies.save()
        else:
            st.session_state["password_correct"] = False

    # Check authentication status  
    if st.session_state.get("password_correct", False):
        return True
    
    # Show password input
    st.text_input(
        "Password", 
        type="password", 
        on_change=password_entered, 
        key="password"
    )
    
    # Show error if password was incorrect
    if st.session_state.get("password_correct") == False:
        st.error("😕 Password errata")
    
    return False

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

# --- Technical Analysis Helper ---
def calculate_technical_signal(hist):
    """
    Calculates signal based on provided history dataframe (must have 'Close').
    Returns: (Signal, Reason)
    """
    if len(hist) < 50:
        return "N/A", "Dati insufficienti (>50 periodi)"

    # Calculate indicators on the fly
    hist = hist.copy()
    hist['SMA_20'] = hist['Close'].rolling(window=20).mean()
    hist['SMA_50'] = hist['Close'].rolling(window=50).mean()
    
    delta = hist['Close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    hist['RSI'] = 100 - (100 / (1 + (gain / loss)))

    # Get last values
    last_close = hist['Close'].iloc[-1]
    last_sma20 = hist['SMA_20'].iloc[-1]
    last_sma50 = hist['SMA_50'].iloc[-1]
    last_rsi = hist['RSI'].iloc[-1]

    # Logic
    signal = "HOLD"
    reason = "Neutrale"
    
    if (last_close > last_sma20 and last_close > last_sma50):
        signal = "BUY"
        reason = "Trend Rialzista"
    elif last_rsi < 30:
        signal = "BUY"
        reason = "Ipervenduto (RSI<30)"
    elif last_close < last_sma50:
        signal = "SELL"
        reason = "Trend Ribassista"
    elif last_rsi > 70:
        signal = "SELL"
        reason = "Ipercomprato (RSI>70)"
        
    return signal, reason

def get_signal_for_dashboard(ticker):
    try:
        stock = yf.Ticker(ticker)
        # Fetch enough history for SMA50 + buffer
        hist = stock.history(period="6mo") 
        if hist.empty:
            return "N/A", ""
        return calculate_technical_signal(hist)
    except:
        return "N/A", "Errore Dati"

# --- AI Helper ---
def ask_gemini(prompt):
    """Uses Groq API for AI analysis (kept function name for compatibility)"""
    if not GROQ_API_KEY:
        return "⚠️ API Key mancante. Inserisci GROQ_API_KEY nel file .env"
    if not groq_client:
        return "⚠️ Client Groq non inizializzato. Verifica GROQ_API_KEY nel file .env"
    try:
        chat_completion = groq_client.chat.completions.create(
            messages=[
                {
                    "role": "user",
                    "content": prompt,
                }
            ],
            model="llama-3.3-70b-versatile",
            temperature=0.7,
            max_tokens=1024,
        )
        return chat_completion.choices[0].message.content
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
        signal, reason = get_signal_for_dashboard(ticker) # Fetch Signal
        
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
            "Previsione": signal,
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
        
        def color_signal(val):
            if val == "BUY": return 'color: green; font-weight: bold'
            if val == "SELL": return 'color: red; font-weight: bold'
            return 'color: gray'

        # Format for nicer display
        st.dataframe(df_display.style.format({
            "Prezzo": "{:.4f}",
            "Var % 1d": "{:+.2f}%",
            "PMC": "{:.4f}",
            "Valore": "{:.2f}",
            "P/L €": "{:+.2f}",
            "P/L %": "{:+.2f}%"
        }).map(color_pl, subset=["P/L €", "P/L %", "Var % 1d"])
          .map(color_signal, subset=["Previsione"]))

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

        # Use shared Helper
        signal, reason = calculate_technical_signal(hist)

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
    
    if not check_password():
        st.stop()
    
    # Auto-refresh every 60 seconds
    if 'last_refresh' not in st.session_state:
        st.session_state.last_refresh = time.time()
    
    current_time = time.time()
    time_since_refresh = current_time - st.session_state.last_refresh
    
    # Auto-refresh after 60 seconds
    if time_since_refresh >= 60:
        st.session_state.last_refresh = current_time
        st.rerun()
    
    # Load Data
    portfolio = load_portfolio()

    # --- SIDEBAR ---
    st.sidebar.title("💼 Portafoglio")
    
    # Display last update time in sidebar (after title)
    st.sidebar.caption(f"🕐 Ultimo aggiornamento: {datetime.fromtimestamp(st.session_state.last_refresh).strftime('%H:%M:%S')}")
    
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
