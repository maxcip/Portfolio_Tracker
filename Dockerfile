# Usa un'immagine base leggera di Python
FROM python:3.9-slim

# Imposta la directory di lavoro nel container
WORKDIR /app

# Copia il file dei requisiti e installa le dipendenze
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copia tutto il codice dell'applicazione
COPY . .

# Espone la porta usata da Streamlit
EXPOSE 8501

# Definisce il comando di avvio
CMD ["python", "-m", "streamlit", "run", "execution/app_stock_tracker.py", "--server.address=0.0.0.0"]
