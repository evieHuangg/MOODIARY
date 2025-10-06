FROM python:3.9-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

RUN apt-get update && apt-get install -y \
    build-essential \
    libfreetype6-dev \
    libpng-dev \
    libopenblas-dev \
    libfontconfig1 \
    fonts-noto-cjk \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY . /app/

RUN pip install --upgrade pip && pip install -r requirements.txt

EXPOSE 5002

CMD ["python", "app.py"]
