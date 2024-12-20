# Развертывание приложения

В данном документе описаны шаги по развертыванию и запуску приложения генератора отзывов как локально, так и на VPS.

## Системные требования

- Python 3.8 или выше
- pip (менеджер пакетов Python)
- Git
- Доступ к интернету (для работы с OpenRouter API)

## Установка

1. Клонируйте репозиторий:
```bash
git clone https://github.com/mlteamurfu2325/practicum-s3.git
cd practicum-s3
```

2. Установите зависимости:
```bash
pip install -r requirements.txt
```

3. Настройка переменных окружения:
   - Создайте файл `.env` в корневой директории проекта
   - Добавьте следующие переменные:
   ```
   OPENROUTER_API_KEY=your_api_key_here
   ```
   Получите API ключ на сайте OpenRouter: https://openrouter.ai/

## Локальный запуск

Для запуска приложения локально выполните команду:
```bash
streamlit run app.py
```

По умолчанию приложение будет доступно по адресу: http://localhost:8501

## Запуск на VPS

### Подготовка сервера

1. Подключитесь к вашему VPS по SSH:
```bash
ssh username@your_server_ip
```

2. Установите Python и pip если они еще не установлены:
```bash
sudo apt update
sudo apt install python3 python3-pip
```

3. Клонируйте репозиторий и установите зависимости как описано выше.

4. Настройте переменные окружения:
```bash
echo "OPENROUTER_API_KEY=your_api_key_here" > .env
```

### Запуск приложения

Для запуска приложения с доступом из внешней сети:
```bash
streamlit run app.py --server.address 0.0.0.0 --server.port 8501
```

Приложение будет доступно по адресу: http://your_server_ip:8501

### Настройка постоянного запуска (опционально)

Для запуска приложения в фоновом режиме можно использовать systemd:

1. Создайте файл сервиса:
```bash
sudo nano /etc/systemd/system/streamlit-review-generator.service
```

2. Добавьте следующее содержимое (замените пути на актуальные):
```ini
[Unit]
Description=Streamlit Review Generator
After=network.target

[Service]
User=your_username
WorkingDirectory=/path/to/practicum-s3
Environment="OPENROUTER_API_KEY=your_api_key_here"
ExecStart=/usr/local/bin/streamlit run app.py --server.address 0.0.0.0 --server.port 8501
Restart=always

[Install]
WantedBy=multi-user.target
```

3. Активируйте и запустите сервис:
```bash
sudo systemctl enable streamlit-review-generator
sudo systemctl start streamlit-review-generator
```

### Настройка безопасности

1. Настройте файрвол, разрешив только необходимый порт:
```bash
sudo ufw allow 8501
```

2. Для дополнительной безопасности рекомендуется:
   - Настроить Nginx как обратный прокси-сервер
   - Настроить SSL-сертификат
   - Защитить файл .env и systemd service файл с API ключом:
   ```bash
   chmod 600 .env
   sudo chmod 600 /etc/systemd/system/streamlit-review-generator.service
   ```

## Проверка работоспособности

После запуска убедитесь, что:
1. Приложение доступно по указанному адресу
2. Все компоненты интерфейса отображаются корректно
3. Форма генерации отзывов работает правильно
4. LLM интеграция работает (проверьте генерацию тестового отзыва)

## Устранение неполадок

1. Если приложение не запускается, проверьте:
   - Установлены ли все зависимости
   - Правильность путей к файлам
   - Наличие необходимых прав доступа
   - Наличие и правильность .env файла
   - Доступность OpenRouter API

2. Если приложение недоступно извне:
   - Проверьте настройки файрвола
   - Убедитесь, что указан правильный адрес сервера (0.0.0.0)
   - Проверьте, что порт 8501 открыт и не занят другим процессом

3. Если не работает генерация отзывов:
   - Проверьте подключение к интернету
   - Проверьте правильность API ключа
   - Проверьте логи на наличие ошибок от OpenRouter API

## Обновление приложения

Для обновления приложения:
```bash
git pull origin main
pip install -r requirements.txt --upgrade
sudo systemctl restart streamlit-review-generator  # если используется systemd
