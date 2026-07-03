FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

COPY requirements.txt ./
RUN pip install --upgrade pip && pip install -r requirements.txt

COPY . .

EXPOSE 8501

CMD ["sh", "-c", "streamlit run main.py --server.port=${STREAMLIT_SERVER_PORT:-8501} --server.address=${STREAMLIT_SERVER_ADDRESS:-0.0.0.0}"]