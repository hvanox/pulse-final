FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY backend_fresh/ ./backend_fresh/
COPY ml/ ./ml/

WORKDIR /app/backend_fresh

ENV JWT_SECRET=""
ENV CORS_ORIGINS="*"
ENV DB_PATH="/data/pulse.db"

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
