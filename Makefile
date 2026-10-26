# Наполнение БД автосервиса: создать CSV/JSON -> пересоздать структуру -> загрузить в SQLite.
#
#   make            # то же, что make all: всё с нуля
#   make data       # только создать файлы в data/
#   make db         # только пересоздать структуру БД (данные будут удалены!)
#   make load       # только загрузить файлы из data/ в уже созданную структуру
#   make stats      # сколько строк в каждой таблице
#   make clean-data # удалить все csv/json из data/
#
# Параметры можно менять в командной строке: make ORDERS=5000 SEED=7

MAKEFLAGS += --no-print-directory
PYTHON ?= python3
DB     ?= db/autoservice.sqlite
SCHEMA ?= lab1/create_tables.sql
ORDERS ?= 2000
SEED   ?= 42

# Порядок загрузки важен из-за внешних ключей: сначала справочники, потом зависимые таблицы.
LOAD_ORDER = model client client_phone automobile service part model_part_compatibility \
             master administrator work_order order_service part_position status_change

.PHONY: all data db load stats clean-data

all:
	$(MAKE) clean-data
	$(MAKE) data
	$(MAKE) db
	$(MAKE) load
	$(MAKE) stats

# Форматы выбраны так, чтобы использовались оба: CSV для плоских таблиц,
# JSON для части остальных. Меняй --format / --*-format, если нужно по-другому.
data:
	$(PYTHON) io/create_catalog.py  --seed $(SEED) --format csv --compat-format json
	$(PYTHON) io/create_services.py --seed $(SEED) --format csv
	$(PYTHON) io/create_staff.py    --seed $(SEED) --format csv --admin-format json
	$(PYTHON) io/create_clients.py  --seed $(SEED) --format csv --phone-format csv --auto-format json
	$(PYTHON) io/create_orders.py   --seed $(SEED) --orders $(ORDERS) --format csv --pp-format json --sc-format json

db:
	$(PYTHON) io/init_db.py --db $(DB) --schema $(SCHEMA)

# Для каждой таблицы берётся существующий файл data/<имя>.csv или data/<имя>.json
load:
	@for t in $(LOAD_ORDER); do \
		f=$$(ls data/$$t.csv data/$$t.json 2>/dev/null | head -n 1); \
		if [ -z "$$f" ]; then echo "Нет файла data/$$t.csv|json, сначала make data"; exit 1; fi; \
		$(PYTHON) io/import.py --file $$f --db $(DB) || exit 1; \
	done

stats:
	@$(PYTHON) io/init_db.py --stats --db $(DB)

# Удаляем и csv, и json: иначе после смены формата останутся устаревшие файлы
clean-data:
	rm -f data/*.csv data/*.json

ruff-c:
	ruff check .

ruff-f:
	ruff check --fix
