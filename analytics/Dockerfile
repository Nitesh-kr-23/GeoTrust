FROM python:3.12-slim

WORKDIR /app

COPY analytics/requirements.txt analytics/requirements.txt
RUN pip install --no-cache-dir -r analytics/requirements.txt

COPY analytics analytics

EXPOSE 8501

CMD streamlit run analytics/dashboard.py --server.address=0.0.0.0 --server.port=${PORT:-8501}
