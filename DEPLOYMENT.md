# Guida al Deployment

Hai due opzioni principali per pubblicare o eseguire questa app in produzione.

## Opzione 1: Streamlit Community Cloud (Gratuito & Consigliato)
Questo è il metodo più semplice per avere l'app online accessibile da chiunque (o privata).

1.  **GitHub**:
    - Crea un repository su GitHub.
    - Carica tutti i file del progetto (assicurati di includere `requirements.txt`).
    - **IMPORTANTE**: NON caricare il file `.env` o la tua API Key pubblica!

2.  **Streamlit Cloud**:
    - Vai su [streamlit.io/cloud](https://streamlit.io/cloud) e accedi.
    - Clicca su "New app".
    - Seleziona il repository GitHub, il branch (es. `main`) e il file principale (`execution/app_stock_tracker.py`).

3.  **Configura i Segreti (API Key)**:
    - Prima di cliccare "Deploy", clicca su "Advanced settings" -> "Secrets".
    - Incolla la tua chiave API in questo formato:
      ```toml
      GEMINI_API_KEY = "la-tua-chiave-qui"
      ```
    - Clicca "Save" e poi "Deploy".

## Opzione 2: Docker (Per Utenti Avanzati / Self-Hosting)
Usa questo metodo se vuoi eseguire l'app su un tuo server (es. VPS Linux, Synology NAS, ecc.) o semplicemente in un container isolato.

### 1. Costruisci l'Immagine
Apri il terminale nella cartella del progetto ed esegui:
```bash
docker build -t stock-portfolio-app .
```

### 2. Esegui il Container
Esegui il comando seguente, sostituendo `TUACHIAVE` con la tua vera API Key di Google Gemini:

```bash
docker run -p 8501:8501 -e GEMINI_API_KEY="TUACHIAVE" stock-portfolio-app
```

Ora apri il browser su `http://localhost:8501`.
