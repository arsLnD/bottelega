#!/bin/bash

# Telegram Bot Auto-Start and Monitor Script
# Скрипт для автозапуска и мониторинга телеграм бота

# Настройки
BOT_DIR="/opt/telegram-bot"
BOT_SCRIPT="bot.py"
PYTHON_PATH="/usr/bin/python3"
LOG_FILE="/var/log/telegram-bot.log"
PID_FILE="/tmp/telegram-bot.pid"
MAX_RESTARTS=5
RESTART_DELAY=10

# Цвета для вывода
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Функция логирования
log_message() {
    echo -e "$(date '+%Y-%m-%d %H:%M:%S') - $1" | tee -a "$LOG_FILE"
}

# Функция проверки зависимостей
check_dependencies() {
    log_message "${BLUE}Проверка зависимостей...${NC}"

    if [ ! -f "$BOT_DIR/requirements.txt" ]; then
        log_message "${RED}Файл requirements.txt не найден!${NC}"
        return 1
    fi

    if [ ! -f "$BOT_DIR/$BOT_SCRIPT" ]; then
        log_message "${RED}Файл бота $BOT_SCRIPT не найден!${NC}"
        return 1
    fi

    # Проверка установки зависимостей
    cd "$BOT_DIR"
    $PYTHON_PATH -c "import aiogram, sqlite3, asyncio" 2>/dev/null
    if [ $? -ne 0 ]; then
        log_message "${YELLOW}Устанавливаем зависимости...${NC}"
        $PYTHON_PATH -m pip install -r requirements.txt
        if [ $? -ne 0 ]; then
            log_message "${RED}Ошибка установки зависимостей!${NC}"
            return 1
        fi
    fi

    return 0
}

# Функция проверки, запущен ли бот
is_bot_running() {
    if [ -f "$PID_FILE" ]; then
        PID=$(cat "$PID_FILE")
        if ps -p "$PID" > /dev/null 2>&1; then
            return 0
        else
            rm -f "$PID_FILE"
            return 1
        fi
    fi
    return 1
}

# Функция запуска бота
start_bot() {
    log_message "${GREEN}Запуск бота...${NC}"

    cd "$BOT_DIR"
    nohup $PYTHON_PATH "$BOT_SCRIPT" >> "$LOG_FILE" 2>&1 &
    BOT_PID=$!
    echo $BOT_PID > "$PID_FILE"

    sleep 3
    if ps -p "$BOT_PID" > /dev/null 2>&1; then
        log_message "${GREEN}Бот успешно запущен с PID: $BOT_PID${NC}"
        return 0
    else
        log_message "${RED}Ошибка запуска бота!${NC}"
        rm -f "$PID_FILE"
        return 1
    fi
}

# Функция остановки бота
stop_bot() {
    if is_bot_running; then
        PID=$(cat "$PID_FILE")
        log_message "${YELLOW}Остановка бота (PID: $PID)...${NC}"
        kill "$PID"
        sleep 5

        if ps -p "$PID" > /dev/null 2>&1; then
            log_message "${YELLOW}Принудительная остановка бота...${NC}"
            kill -9 "$PID"
        fi

        rm -f "$PID_FILE"
        log_message "${GREEN}Бот остановлен${NC}"
    else
        log_message "${YELLOW}Бот не запущен${NC}"
    fi
}

# Функция перезапуска бота
restart_bot() {
    log_message "${BLUE}Перезапуск бота...${NC}"
    stop_bot
    sleep 2
    start_bot
}

# Функция мониторинга
monitor_bot() {
    local restart_count=0

    log_message "${BLUE}Начинаем мониторинг бота...${NC}"

    while true; do
        if ! is_bot_running; then
            log_message "${RED}Бот не запущен! Попытка перезапуска ($restart_count/$MAX_RESTARTS)...${NC}"

            if [ $restart_count -lt $MAX_RESTARTS ]; then
                start_bot
                if [ $? -eq 0 ]; then
                    restart_count=0
                    log_message "${GREEN}Бот успешно перезапущен${NC}"
                else
                    restart_count=$((restart_count + 1))
                    log_message "${RED}Ошибка перезапуска. Попытка $restart_count из $MAX_RESTARTS${NC}"
                fi
            else
                log_message "${RED}Достигнуто максимальное количество попыток перезапуска. Остановка мониторинга.${NC}"
                break
            fi
        fi

        sleep $RESTART_DELAY
    done
}

# Функция показа статуса
show_status() {
    echo -e "${BLUE}=== Статус Telegram бота ===${NC}"

    if is_bot_running; then
        PID=$(cat "$PID_FILE")
        echo -e "Статус: ${GREEN}Запущен${NC}"
        echo -e "PID: $PID"
        echo -e "Время работы: $(ps -o etime= -p "$PID" 2>/dev/null || echo 'Неизвестно')"
        echo -e "Использование памяти: $(ps -o rss= -p "$PID" 2>/dev/null || echo 'Неизвестно') KB"
    else
        echo -e "Статус: ${RED}Остановлен${NC}"
    fi

    echo -e "Лог файл: $LOG_FILE"
    echo -e "PID файл: $PID_FILE"
    echo -e "Директория бота: $BOT_DIR"
}

# Функция показа логов
show_logs() {
    local lines=${1:-50}
    echo -e "${BLUE}=== Последние $lines строк лога ===${NC}"
    if [ -f "$LOG_FILE" ]; then
        tail -n "$lines" "$LOG_FILE"
    else
        echo -e "${YELLOW}Лог файл не найден${NC}"
    fi
}

# Функция установки cron задачи
install_cron() {
    local script_path=$(realpath "$0")
    local cron_job="*/5 * * * * $script_path monitor >/dev/null 2>&1"

    (crontab -l 2>/dev/null; echo "$cron_job") | crontab -
    log_message "${GREEN}Cron задача установлена для автоматического мониторинга${NC}"
}

# Функция удаления cron задачи
remove_cron() {
    local script_path=$(realpath "$0")
    crontab -l 2>/dev/null | grep -v "$script_path" | crontab -
    log_message "${GREEN}Cron задача удалена${NC}"
}

# Функция показа справки
show_help() {
    echo -e "${BLUE}=== Telegram Bot Manager ===${NC}"
    echo "Использование: $0 {start|stop|restart|status|logs|monitor|install-cron|remove-cron|help}"
    echo ""
    echo "Команды:"
    echo "  start        - Запустить бота"
    echo "  stop         - Остановить бота"
    echo "  restart      - Перезапустить бота"
    echo "  status       - Показать статус бота"
    echo "  logs [N]     - Показать последние N строк лога (по умолчанию 50)"
    echo "  monitor      - Запустить мониторинг (бесконечный цикл)"
    echo "  install-cron - Установить автоматический мониторинг через cron"
    echo "  remove-cron  - Удалить автоматический мониторинг"
    echo "  help         - Показать эту справку"
}

# Создание необходимых директорий и файлов
mkdir -p "$(dirname "$LOG_FILE")"
touch "$LOG_FILE"

# Основная логика
case "$1" in
    start)
        if is_bot_running; then
            log_message "${YELLOW}Бот уже запущен${NC}"
            show_status
        else
            if check_dependencies; then
                start_bot
            fi
        fi
        ;;
    stop)
        stop_bot
        ;;
    restart)
        if check_dependencies; then
            restart_bot
        fi
        ;;
    status)
        show_status
        ;;
    logs)
        show_logs "$2"
        ;;
    monitor)
        if check_dependencies; then
            if ! is_bot_running; then
                start_bot
            fi
            monitor_bot
        fi
        ;;
    install-cron)
        install_cron
        ;;
    remove-cron)
        remove_cron
        ;;
    help|--help|-h)
        show_help
        ;;
    *)
        echo -e "${RED}Неизвестная команда: $1${NC}"
        show_help
        exit 1
        ;;
esac

exit 0
