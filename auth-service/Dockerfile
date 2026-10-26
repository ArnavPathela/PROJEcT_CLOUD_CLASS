FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY app.py .
ENV PORT=5001 DB_PATH=/data/auth.db
RUN mkdir /data
EXPOSE 5001
HEALTHCHECK --interval=15s --timeout=3s --retries=5 CMD python -c "import os,urllib.request;urllib.request.urlopen('http://localhost:%s/health'%os.environ['PORT'])" || exit 1
CMD ["sh", "-c", "gunicorn -b 0.0.0.0:${PORT} app:app"]
