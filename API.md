# Маршруты приложения "СтройКонтроль"

## Публичные маршруты

| GET | `/` | Перенаправление на вход или панель |
| GET | `/login` | Страница входа |
| POST | `/login` | Обработка формы входа |

## Защищённые маршруты (требуют авторизации)

| Метод | Путь | Роль | Описание |
|-------|------|------|----------|
| GET | `/dashboard` | Все | Панель управления |
| GET | `/orders` | Все | Список заказов |
| GET | `/order/create` | admin, manager | Форма создания заказа |
| POST | `/order/create` | admin, manager | Сохранение заказа |
| GET | `/order/<id>` | Все | Детали заказа |
| POST | `/order/<id>/update_status` | admin, manager | Смена статуса |
| GET | `/warehouse` | admin, logist | Склад материалов |
| POST | `/warehouse` | admin, logist | Добавление/резерв материала |
| GET | `/reports` | admin, director | Страница отчётов |
| GET | `/export/orders` | admin, director, manager | Экспорт заказов (CSV) |
| GET | `/export/tax` | admin, director | Экспорт налоговой отчётности (CSV) |
| GET | `/export/statistics` | admin, director | Экспорт статистики (CSV) |
| GET | `/logout` | Все | Выход из системы |

## Формат данных

### Создание заказа (POST /order/create)