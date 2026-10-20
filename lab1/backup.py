"""Резервное копирование базы данных SQLite.

Каждая копия сохраняется в отдельную папку с датой и временем в названии:
    backups/2026-10-20_10-34-00/autoservice.sqlite

Запуск из любого места:
    python lab1/backup.py                                  # сделать резервную копию
    python lab1/backup.py list                             # показать все копии
    python lab1/backup.py restore                          # восстановить из последней копии
    python lab1/backup.py restore 2026-10-20_10-34-00      # восстановить из конкретной копии

Перед восстановлением скрипт сам делает копию текущей базы в папку before-restore_<дата_время>
(на случай, если восстанавливать не стоило). Такие копии не считаются «последней» для restore.
Соединение с базой в DBeaver на время восстановления
лучше закрыть, иначе SQLite ответит «database is locked».
Копирование идёт через встроенный механизм резервного копирования sqlite3,
поэтому копия получается целостной, даже если база открыта.
"""
import argparse
import sqlite3
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_DB = ROOT / "db" / "autoservice.sqlite"
DEFAULT_DIR = ROOT / "backups"


def row_counts(db_path):
    """Число строк в каждой таблице: так проверяем, что копия совпадает с оригиналом."""
    conn = sqlite3.connect(db_path.resolve().as_uri() + "?mode=ro", uri=True)
    try:
        tables = [r[0] for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name")]
        return {t: conn.execute(f'SELECT COUNT(*) FROM "{t}"').fetchone()[0] for t in tables}
    finally:
        conn.close()


def copy_db(src_path, dst_path):
    """Копирует базу целиком через sqlite3.backup."""
    src = sqlite3.connect(src_path.resolve().as_uri() + "?mode=ro", uri=True)
    dst = sqlite3.connect(dst_path)
    try:
        src.backup(dst)
    finally:
        dst.close()
        src.close()


SAFETY_PREFIX = "before-restore_"   # копии, сделанные автоматически перед восстановлением


def make_backup(db_path, backups_dir, prefix=""):
    """Создаёт папку backups/<дата_время>/ и кладёт туда копию базы. Возвращает путь к копии."""
    if not db_path.exists():
        sys.exit(f"База не найдена: {db_path}")
    stamp = prefix + datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    folder = backups_dir / stamp
    n = 1
    while folder.exists():                                  
        folder = backups_dir / f"{stamp}_{n}"
        n += 1
    folder.mkdir(parents=True)
    target = folder / db_path.name
    copy_db(db_path, target)
    return target


def list_backups(backups_dir):
    if not backups_dir.exists():
        return []
    return sorted(p for p in backups_dir.iterdir() if p.is_dir() and any(p.glob("*.sqlite")))


def report_check(label_a, counts_a, label_b, counts_b):
    total_a, total_b = sum(counts_a.values()), sum(counts_b.values())
    ok = counts_a == counts_b
    print(f"Проверка: {label_a} - {total_a} строк, {label_b} - {total_b} строк -> "
          f"{'совпадает' if ok else 'НЕ СОВПАДАЕТ'}")
    return ok


def main():
    parser = argparse.ArgumentParser(description="Резервное копирование базы SQLite")
    parser.add_argument("command", nargs="?", default="backup", choices=["backup", "list", "restore"])
    parser.add_argument("name", nargs="?", help="имя папки копии для restore (по умолчанию последняя)")
    parser.add_argument("--db", default=str(DEFAULT_DB), help="путь к файлу базы")
    parser.add_argument("--dir", default=str(DEFAULT_DIR), help="папка для резервных копий")
    args = parser.parse_args()
    db_path, backups_dir = Path(args.db), Path(args.dir)

    if args.command == "backup":
        target = make_backup(db_path, backups_dir)
        print(f"Резервная копия создана: {target}")
        if not report_check("база", row_counts(db_path), "копия", row_counts(target)):
            sys.exit(1)

    elif args.command == "list":
        found = list_backups(backups_dir)
        if not found:
            print(f"Копий нет в {backups_dir}")
        for p in found:
            print(p.name)

    else:  # restore
        found = list_backups(backups_dir)
        if not found:
            sys.exit(f"Копий нет в {backups_dir}")
        regular = [p for p in found if not p.name.startswith(SAFETY_PREFIX)]
        if not args.name and not regular:
            sys.exit(f"Обычных копий нет в {backups_dir}, укажите имя папки вручную")
        folder = backups_dir / args.name if args.name else regular[-1]   # «последняя» без страховочных
        source = folder / db_path.name
        if not source.exists():
            sys.exit(f"В копии нет файла {db_path.name}: {folder}")
        if db_path.exists():
            safety = make_backup(db_path, backups_dir, prefix=SAFETY_PREFIX)
            print(f"Текущая база сохранена на всякий случай: {safety}")
        try:
            copy_db(source, db_path)
        except sqlite3.OperationalError as e:
            sys.exit(f"Не удалось восстановить ({e}). Закройте соединение с базой в DBeaver и повторите.")
        print(f"База восстановлена из {folder.name}")
        if not report_check("копия", row_counts(source), "база", row_counts(db_path)):
            sys.exit(1)


if __name__ == "__main__":
    main()
