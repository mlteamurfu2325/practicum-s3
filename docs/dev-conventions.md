# Соглашения (конвенции) по разработке
## Флоу разработки в репозитории

### Алгоритм работы с репозиторием:
1. Создаём issue: https://github.com/mlteamurfu2325/practicum-s3/issues/new/choose

2. Создаём ветку с названием `issue-<номер issue>/<category>/<краткое описание>`

3. Разрабатываем функционал в ветке

4. Создаём pull request: https://github.com/mlteamurfu2325/practicum-s3/compare

5. Проводим code review (выбираем одного из членов команды)

6. Сливаем ветку в main

7. Закрываем issue

### Примеры наименования веток
```
issue-1/docs/add-cqa-and-project-conventions
issue-2/feat/add-postgress-pipeline
issue-3/fix/fix-bug-with-data-loading
```
Категория ветки (`docs`, `feat`, `fix`) выбирается из типов коммитов (см. ниже).


## Правила именования коммитов

Соглашение о правилах именования коммитов в нашем проекте.

### Структура commit message

```
<тип>[область]: <описание>

[дополнительное описание]

[BREAKING CHANGE: <описание ломающих изменений>]
```

### Типы коммитов

- `feat` - добавление новой функциональности
- `fix` - исправление ошибок
- `docs` - изменения в документации
- `style` - форматирование кода, исправление отступов (не влияет на логику)
- `refactor` - рефакторинг кода
- `test` - добавление или изменение тестов
- `chore` - обслуживание кода/проекта (обновление зависимостей, настройка CI и т.д.)
- `perf` - улучшения производительности
- `ci` - изменения в CI/CD конфигурации
- `build` - изменения в системе сборки
- `revert` - откат предыдущих изменений

### Область (scope)

Область указывает на часть проекта, которой касаются изменения. Например:

- `auth` - аутентификация
- `api` - API endpoints
- `db` - база данных
- `ui` - пользовательский интерфейс
- `utils` - утилиты
- и т.д.

### Примеры

```
feat(auth): add OAuth2 support

fix(db): correct insert logic in PostgreSQL

docs: update API docs

style: add code formatting in black

refactor(utils): rewrite helper function

test(api): add tests for new endpoints

chore: update dependencies in requirements.txt

perf(api): optimize SQL queries
```

### Правила написания описаний

1. Используйте повелительное наклонение: "add", "correct", "update"
2. Не ставьте точку в конце описания
3. Первая строка должна быть не длиннее 72 символов
4. Описывайте изменения кратко и по существу
5. При необходимости используйте дополнительное описание после пустой строки

### Breaking Changes

Если ваши изменения нарушают обратную совместимость:

1. Добавьте `!` после типа: `feat!: remove deprecated API endpoint`
2. Добавьте `BREAKING CHANGE:` в теле коммита с описанием изменений

### Полезные инструменты

- [conventional-pre-commit](https://github.com/compilerla/conventional-pre-commit) - проверка коммитов с помощью pre-commit

### Дополнительные ресурсы

- [Conventional Commits](https://www.conventionalcommits.org/)


## pre-commit как инструмент контроля качества кода

Для обеспечения нужного уровня качества кода в проекте мы используем инструмент `pre-commit`. Этот инструмент позволяет автоматически проверять и форматировать код перед его коммитом.

Установка `pre-commit`:
1. Установите `pre-commit` с помощью pip:
```bash
pip install pre-commit
```
2. Проверьте, что в Вашей копии нашего репозитория находится верхнеуровнеый файл `.pre-commit-config.yaml`.
3. Установите хуки `pre-commit` в локальный репозиторий:
```bash
pre-commit install
```

Использование `pre-commit`:
1. Каждый раз при коммите изменений в репозиторий `pre-commit` будет автоматически запускать проверки и форматирование кода.
2. Если проверки не пройдены, коммит будет отменен.
3. Вы можете запустить проверки и форматирование кода вручную с помощью команды:
```bash
pre-commit run --all-files
```

### Дополнительные ресурсы

- [pre-commit](https://pre-commit.com/)
