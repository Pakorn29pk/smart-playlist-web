FROM python:3.11-slim
WORKDIR /app
COPY playlist.py server.py ./
COPY static ./static
COPY sample_data ./sample_data
ENV PYTHONUNBUFFERED=1 PORT=8000
EXPOSE 8000
CMD ["python", "server.py"]
