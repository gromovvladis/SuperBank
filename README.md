**Тестовое задание** 

*Реализовано на Django + DRF.*

Для запуска: 
  Docker Compose команды:
  1. Запуск: docker-compose up --build
  2. Остановка: docker-compose down
  3. Очистка всех volumes: docker-compose down -v
  4. Запуск тестов: docker-compose exec web python manage.py test apps .

Реализовано два эндпоинта.
  1. Получения баланса кошелька.
  2. Создание транзакции пополнения и изъятия средств.

В базе данных хранится информация о кошельке и всех его транзакциях.

При запуске проекта из Dockerfile применяются фикстуры: создаётся один кошелек с ненулевым балансом и несколько транзакций.
Создание дополнительных кошельков доступно через админ-панель Django.

Для тестирования можно обратиться к кошельку из фикстур по его UUID:
6474f08c-8bec-4628-8b84-a6695b18109e

Для доступа к админ панели можно использовать данные пользователя:
  login: bankuser
  pass: 1234

Для избежания Race Condition транзакция (создание объекта транзакции и изменение баланса кошелька) выполняется атомарно.

Написаны тесты для:
  1. Функционал кошелька
  2. Эндпоинты
