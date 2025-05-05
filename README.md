# MWAN3 Telegram Bot

Простой Telegram-бот для роутера с OpenWRT, который отслеживает переключение между основным и резервным интернет-каналом через `mwan3` и отправляет уведомления в Telegram.

## Возможности

- Уведомляет в Telegram при переключении каналов (основной/резервный)
- Собирает статистику по количеству переключений и времени на резервном канале
- Отвечает на команду `/status` — показывает статистику за сегодня и текущий месяц
- Автоматически сбрасывает статистику:
  - Ежедневно очищает старые данные
  - В первый день месяца очищает весь файл статистики
- Очищает лог-файл `bot.log` ежедневно
- Хранит состояние и статистику в файлах (`state.json`, `stats.json`) которые сам и создает

## Установка

1. Создайте директорию:
```
mkdir /root/mwan3bot
```
```
cd /root/mwan3bot
```
Клонируйте репозиторий на роутер:
```
git clone https://github.com/jvckdubz/mwan3-telegram-bot.git
```
*для создания файлов вручную потребуются только bot.py и event-hook.sh

2. Установите зависимости:

```
opkg update
opkg install python3 python3-pip ca-bundle
pip3 install requests
```

3. В `bot.py` замените `ВАШ_ТОКЕН` и `ВАШ_CHAT_ID` на ваши значения от Telegram-бота.

4. Запустите бота:

```
python3 bot.py
```
Создаем службу:
```
nano /etc/init.d/mwan3bot
```
Вставляем содержимое файла 'etc-init.d-mwan3bot'
```
/etc/init.d/mwan3bot enable
```
```
/etc/init.d/mwan3bot start
```

## Интеграция с mwan3

Для автоматического уведомления о переключении каналов добавьте следующий код в файл `/etc/mwan3.user`:

```sh
#!/bin/sh
logger -t mwan3.user "$ACTION interface $INTERFACE"

MAIN_IF="wan"
RESERVE_IF="wan2"

if [ "$ACTION" = "ifdown" ] && [ "$INTERFACE" = "$MAIN_IF" ]; then
    /root/mwan3bot/event-hook.sh to_reserve "$RESERVE_IF"
elif [ "$ACTION" = "ifup" ] && [ "$INTERFACE" = "$MAIN_IF" ]; then
    /root/mwan3bot/event-hook.sh to_main
fi
```

Замените `wan` и `wan2` на названия ваших интерфейсов, если они отличаются.

Этот скрипт будет вызываться при смене состояния основного интерфейса и передавать информацию в бота через `event-hook.sh`.

Альтернативно можно вручную вызвать изменение состояния:

```sh
curl "http://localhost:8081/?state=main"
```
или

```sh
curl "http://localhost:8081/?state=reserve"
```

## Файлы

- `bot.py` — основной код бота
- `event-hook.sh` — вызывается системой при переключении
- `state.json` — текущее состояние (создаётся автоматически)
- `stats.json` — статистика за дни и месяцы (создаётся автоматически)
- `bot.log` — лог-файл (опционально)

## License

This project is licensed under the MIT License - see the [LICENSE](./LICENSE) file for details.
