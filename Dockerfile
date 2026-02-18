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

# Устанавливаем ChromeDriver
RUN CHROME_VERSION=$(google-chrome --version | sed -E 's/.* ([0-9]+\.[0-9]+\.[0-9]+\.[0-9]+).*/\1/') \
    && echo "Chrome version: $CHROME_VERSION" \
    && wget -q -O /tmp/chromedriver.zip \
    "https://edgedl.me.gvt1.com/edgedl/chrome/chrome-for-testing/${CHROME_VERSION}/linux64/chromedriver-linux64.zip" \
    && unzip /tmp/chromedriver.zip -d /tmp/ \
    && mv /tmp/chromedriver-linux64/chromedriver /usr/local/bin/chromedriver \
    && chmod +x /usr/local/bin/chromedriver \
    && rm -rf /tmp/chromedriver*

WORKDIR /app

# Сначала установим только необходимые для сборки пакеты
COPY requirements.txt .

# Обновляем pip и устанавливаем wheel
RUN pip install --no-cache-dir --upgrade pip wheel setuptools

# Устанавливаем Cython отдельно (нужен для некоторых пакетов)
RUN pip install --no-cache-dir Cython

# Теперь устанавливаем остальные зависимости с предпочтением бинарных пакетов
RUN pip install --no-cache-dir --prefer-binary -r requirements.txt

# Копируем остальной код
COPY . .

# Создаем директории
RUN mkdir -p logs downloads data keywords chrome_profile

# Переменные окружения
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app
ENV CHROME_BIN=/usr/bin/google-chrome-stable
ENV CHROMEDRIVER_PATH=/usr/local/bin/chromedriver
ENV DISPLAY=:99
ENV HEADLESS=true

# Создаем пользователя для безопасности
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

CMD ["python", "main.py"]