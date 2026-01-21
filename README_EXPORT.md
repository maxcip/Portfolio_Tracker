# Guida all'Esportazione e Installazione

Per eseguire questa app su un altro computer, segui questi passaggi:

## 1. Copia i File
Copia l'intera cartella `Antigravity` sul nuovo computer. Assicurati che siano presenti:
- `execution/app_stock_tracker.py`
- `portfolio.csv` (i tuoi dati)
- `.env` (la tua chiave API, se vuoi usare l'AI)
- `requirements.txt`

## 2. Installa Python
Assicurati di avere Python installato (scaricalo da [python.org](https://www.python.org)). Durante l'installazione, spunta "Add Python to PATH".

## 3. Installa le Dipendenze
Apri il terminale (o Prompt dei Comandi) nella cartella copiata ed esegui:
```bash
pip install -r requirements.txt
```

## 4. Avvia l'App
Sempre dal terminale, esegui:
```bash
python -m streamlit run execution/app_stock_tracker.py
```

L'app si aprirà nel browser!
