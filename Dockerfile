# Используем Python 3.13
FROM python:3.13-slim-bookworm

# Устанавливаем системные зависимости
RUN apt-get update && apt-get install -y \
    wget \
    gnupg \
    ca-certificates \
    # Для компиляции Python пакетов
    gcc \
    g++ \
    make \
    pkg-config \
    python3-dev \
    # Зависимости для Chrome
    libxss1 \
    libasound2 \
    libnspr4 \
    libnss3 \
    libx11-xcb1 \
    libxcomposite1 \
    libxcursor1 \
    libxdamage1 \
    libxi6 \
    libxtst6 \
    libatk-bridge2.0-0 \
    libgtk-3-0 \
    libgbm1 \
    libdrm2 \
    libxrandr2 \
    # Для работы с архивами
    unzip \
    zip \
    curl \
    --no-install-recommends \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Устанавливаем Google Chrome
RUN wget -q -O /tmp/chrome.deb \
    "https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb" \
    && apt-get update \
    && apt-get install -y /tmp/chrome.deb \
    && rm /tmp/chrome.deb \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Проверяем установку Chrome
RUN google-chrome --version

WORKDIR /app

# Копируем requirements и устанавливаем зависимости
COPY requirements.txt .

# Обновляем pip и устанавливаем все зависимости
RUN pip install --no-cache-dir --upgrade pip wheel setuptools && \
    pip install --no-cache-dir --prefer-binary -r requirements.txt

# Копируем весь код
COPY . .

# Создаем необходимые директории
RUN mkdir -p logs downloads data keywords chrome_profile

# Устанавливаем правильные права
RUN chmod -R 777 logs downloads data keywords chrome_profile

# Переменные окружения
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app
ENV CHROME_BIN=/usr/bin/google-chrome
ENV DISPLAY=:99
ENV SELENIUM_HEADLESS=true
ENV WDM_LOG_LEVEL=0

# Создаем пользователя для безопасности
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

CMD ["python", "main.py"]