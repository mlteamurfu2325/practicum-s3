# 🔬 Проектный практикум №3 (группа №3 УрФУ)

## 📝 Решаемая задача

Нашей командой выполняется учебная задача:


> Создать нейронную сеть, способную генерировать текстовые отзывы о различных местах на основе определенных входных параметров, таких как категория места, средний рейтинг и ключевые слова.


🗃️ Данные: https://github.com/yandex/geo-reviews-dataset-2023

## 👥 Состав команды
Команда состоит из 5-и человек (группа №3 УрФУ):
- [Кирилл Хитрин](https://github.com/khit-mle)
- [Алексей Горбачев](https://github.com/ANGorbachev)
- [Данил Хардин](https://github.com/DanilKhardi)
- [Елена Икрина](https://github.com/LenaIkra)
- [Александра Антонова](https://github.com/alexa313)

## 💼 Зоны ответственности
| Направление | Ответственный |
|----------|--------|
| Core Development | @khit-mle |
| Architecture Design and Dev | @DanilKhardi |
| Front-end Development | @ANGorbachev |
| Documentation and QA | @alexa313 |
| DevOps and QA | @LenaIkra |

## 🖥️ Стенд с развёрнутым приложением
https://reviews-generator-team-3.myaddr.dev/

## 📓 Автообновляемый ipynb-ноутбук с EDA
https://nbviewer.org/github/mlteamurfu2325/practicum-s3/blob/gh-pages/eda/yandex-reviews-eda.ipynb

## 🖼️ Презентация по выполненному проекту
https://docs.google.com/presentation/d/1iysaqwCSbldqxW4BaKkUrdGh9QhORRrCMj7YErHMuZs/edit?usp=sharing

## 🚀 Инструкция по развёртыванию приложения

<details>
  <summary>👈 Прочитать инструкцию можно здесь</summary>

Для развёртывания приложения необходима машина (физическая, виртуальная, VPS) с установленным дистрибутивом Ubuntu 24.04 и пакетами `python3`, `python3-virtualenv`, `python3-pip`, `wget`. Кроме того, доступной должна быть команда `md5sum`.

В новой директории выполняем клонирование репозитория в текущую директорию:
```sh
git clone https://github.com/mlteamurfu2325/practicum-s3.git .
```

Далее рекомендуем скачать готовый Parquet-файл, который содержит как исходные отзывы от Яндекса, так и колонку эмбеддингов, сгенерированных на основе значений колонки `text`: https://mega.nz/file/WVB3gIDT#NDUcZMcCCEla7mtpvAdk2ecMkQ0oOgtDMoSBa1dglDA

Скаченный файл необходимо поместить в директорию `data/`.

В случае отсутствия данного файла деплоймент-скрипт скачает исходный TSKV-файл из репозитория Яндекса, а затем запустит на нём процедуру эмбеддингования. В таком случае очень желательно наличие GPU (тесты проводились на VPS с посекундной арендой RTX 4090, в случае наличия менее мощного GPU, необходимо уменьшить значение `BATCH_SIZE` в файле `src/reviews-processing/enrich_with_embeddings.py`).

Затем запускаем деплоймент-скрипт:
```sh
bash deployment.sh
```

Далее необходимо установить docker и docker compose в соответствии с официальной инструкцией: https://docs.docker.com/engine/install/ubuntu/

После этого запускаем контейнер:
```sh
cd docker/

docker compose up -d

cd ..
```

Далее импортируем данные в PostgreSQL:
```sh
source .venv/bin/activate

python src/db-importer/pg-reviews-importer.py
```

Устанавливаем значение API ключа сервиса доступа к LLM:
```sh
echo "OPENROUTER_API_KEY=XYZ" > .env
```

Запускаем Streamlit с доступов для внешних IP:
```sh
streamlit run app.py --server.address 0.0.0.0 --server.port 8501
```

</details>

## ⚙️ Актуальное состояние проекта
На текущий момент нами подготовлен MVP-вариант приложения, с которым можно ознакомиться по ссылке, указанной выше.

Реализованный функционал:
- UI для пользовательского взаимодействия по генерации отзыва;
- логика развёртывания приложения;
- генерация эмбеддингов с помощью модели "sergeyzh/rubert-tiny-turbo";
- LangGraph-основанный подход по валидации пользовательских данных, генерации отзыва с обогащением контекста реальными релевантными отзывами; самопроверка сгенерированного текста моделью; см. `docs/llm_integration.md`
- показ пользователю в отладочных целях использованных для генерации реальных отзывов.

Разработка осуществляется через создание Issues ([ссылка на наши закрытые](https://github.com/mlteamurfu2325/practicum-s3/issues?q=is%3Aissue+is%3Aclosed)) в репозитории и вливание тематических веток в `main` через Pull Requests ([ссылка на вмерженные](https://github.com/mlteamurfu2325/practicum-s3/pulls?q=is%3Apr+is%3Aclosed)).

## 📜 Самопроверка по критериям промежуточной сдачи
| Критерий | Самопроверка |
|----------|--------|
| Есть репозиторий с черновиком решения, в нем указан состав команды и зоны ответственности, актуальное состояние проекта | ✅ |
| Самооценка архитектуры предложенного решения, codereview | ✅ |
| Самооценка качества кода, качества документации | ✅ |

## 📜 Самопроверка по критериям финальной сдачи
| Критерий | Самопроверка |
|----------|--------|
| Очистка и подготовка данных | ✅ |
| Качество модели и генерации текстов | ✅ |
| Процесс обучения и оптимизация | ✅ |
| Качество кода | ✅ |