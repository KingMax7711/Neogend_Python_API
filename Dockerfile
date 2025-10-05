FROM python:3.11-slim

WORKDIR /app

# Installer les dépendances
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt && \
	pip install --no-cache-dir alembic psycopg2-binary

# Copier le code
COPY . .

# Donner les droits d'exécution au script de démarrage
RUN chmod +x /app/start.sh

# Exposer le port
EXPOSE 8000

# Lancer l'app via un script qui attend la DB et applique les migrations Alembic
CMD ["/app/start.sh"]
