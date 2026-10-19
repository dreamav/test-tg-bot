"""Асинхронный модуль работы с базой данных SQLite."""

from contextlib import asynccontextmanager
import datetime
from typing import Any, AsyncGenerator
import aiosqlite
from config import config
from database.models import (
    CREATE_APPOINTMENTS_TABLE,
    CREATE_SLOTS_TABLE,
    CREATE_WORKING_DAYS_TABLE,
)


class Database:
    """Класс для асинхронного взаимодействия с базой данных SQLite."""

    def __init__(self, db_path: str = config.DATABASE_PATH):
        self.db_path = db_path

    @asynccontextmanager
    async def _get_connection(self) -> AsyncGenerator[aiosqlite.Connection, None]:
        """Асинхронный контекстный менеджер подключения к БД."""
        conn = await aiosqlite.connect(self.db_path)
        conn.row_factory = aiosqlite.Row
        await conn.execute("PRAGMA foreign_keys = ON;")
        try:
            yield conn
        finally:
            await conn.close()

    async def init_db(self) -> None:
        """Инициализация таблиц базы данных."""
        async with self._get_connection() as conn:
            await conn.execute(CREATE_WORKING_DAYS_TABLE)
            await conn.execute(CREATE_SLOTS_TABLE)
            await conn.execute(CREATE_APPOINTMENTS_TABLE)
            await conn.commit()

    # ------------------ Рабочие дни ------------------

    async def is_day_closed(self, date_str: str) -> bool:
        """Проверить, закрыт ли день для записи."""
        async with self._get_connection() as conn:
            cursor = await conn.execute(
                "SELECT is_closed FROM working_days WHERE date = ?", (date_str,)
            )
            row = await cursor.fetchone()
            if row is not None:
                return bool(row["is_closed"])
            return False

    async def toggle_day_closed(self, date_str: str) -> bool:
        """Переключить статус дня: закрыт / открыт. Возвращает новое состояние (True - закрыт)."""
        async with self._get_connection() as conn:
            cursor = await conn.execute(
                "SELECT is_closed FROM working_days WHERE date = ?", (date_str,)
            )
            row = await cursor.fetchone()
            if row is None:
                # По умолчанию открыт, делаем закрытым
                new_status = 1
                await conn.execute(
                    "INSERT INTO working_days (date, is_closed) VALUES (?, ?)",
                    (date_str, new_status),
                )
            else:
                new_status = 0 if row["is_closed"] else 1
                await conn.execute(
                    "UPDATE working_days SET is_closed = ? WHERE date = ?",
                    (new_status, date_str),
                )
            await conn.commit()
            return bool(new_status)

    async def get_closed_dates(self, start_date: str, end_date: str) -> set[str]:
        """Получить множество закрытых дат в диапазоне."""
        async with self._get_connection() as conn:
            cursor = await conn.execute(
                "SELECT date FROM working_days WHERE date BETWEEN ? AND ? AND is_closed = 1",
                (start_date, end_date),
            )
            rows = await cursor.fetchall()
            return {row["date"] for row in rows}

    # ------------------ Слоты времени ------------------

    async def add_slot(self, date_str: str, time_str: str) -> bool:
        """Добавить временной слот на дату. Возвращает True, если добавлен."""
        async with self._get_connection() as conn:
            try:
                await conn.execute(
                    "INSERT INTO slots (date, time, is_booked) VALUES (?, ?, 0)",
                    (date_str, time_str),
                )
                await conn.commit()
                return True
            except aiosqlite.IntegrityError:
                return False

    async def add_slots_batch(self, date_str: str, times: list[str]) -> int:
        """Добавить список временных слотов. Возвращает количество добавленных."""
        count = 0
        async with self._get_connection() as conn:
            for time_str in times:
                try:
                    await conn.execute(
                        "INSERT INTO slots (date, time, is_booked) VALUES (?, ?, 0)",
                        (date_str, time_str),
                    )
                    count += 1
                except aiosqlite.IntegrityError:
                    continue
            await conn.commit()
        return count

    async def delete_slot(self, slot_id: int) -> bool:
        """Удалить слот, если на него нет активной записи."""
        async with self._get_connection() as conn:
            # Проверяем, свободен ли слот
            cursor = await conn.execute(
                "SELECT is_booked FROM slots WHERE id = ?", (slot_id,)
            )
            row = await cursor.fetchone()
            if not row or row["is_booked"] == 1:
                return False

            await conn.execute("DELETE FROM slots WHERE id = ?", (slot_id,))
            await conn.commit()
            return True

    async def get_slot_by_id(self, slot_id: int) -> dict[str, Any] | None:
        """Получить слот по ID."""
        async with self._get_connection() as conn:
            cursor = await conn.execute("SELECT * FROM slots WHERE id = ?", (slot_id,))
            row = await cursor.fetchone()
            return dict(row) if row else None

    async def get_all_slots_for_date(self, date_str: str) -> list[dict[str, Any]]:
        """Получить все слоты на дату (и свободные, и занятые), упорядоченные по времени."""
        async with self._get_connection() as conn:
            cursor = await conn.execute(
                "SELECT * FROM slots WHERE date = ? ORDER BY time ASC", (date_str,)
            )
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]

    async def get_available_slots(self, date_str: str) -> list[dict[str, Any]]:
        """Получить только доступные для записи слоты на дату."""
        if await self.is_day_closed(date_str):
            return []
        async with self._get_connection() as conn:
            cursor = await conn.execute(
                "SELECT * FROM slots WHERE date = ? AND is_booked = 0 ORDER BY time ASC",
                (date_str,),
            )
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]

    async def get_dates_with_available_slots(
        self, start_date: str, end_date: str
    ) -> set[str]:
        """Получить множество дат, у которых есть хотя бы 1 свободный слот и день не закрыт."""
        async with self._get_connection() as conn:
            query = """
            SELECT DISTINCT s.date
            FROM slots s
            LEFT JOIN working_days w ON s.date = w.date
            WHERE s.date BETWEEN ? AND ?
              AND s.is_booked = 0
              AND (w.is_closed IS NULL OR w.is_closed = 0)
            """
            cursor = await conn.execute(query, (start_date, end_date))
            rows = await cursor.fetchall()
            return {row["date"] for row in rows}

    # ------------------ Записи (Appointments) ------------------

    async def get_active_appointment_by_user(
        self, user_id: int
    ) -> dict[str, Any] | None:
        """Получить активную запись пользователя."""
        async with self._get_connection() as conn:
            cursor = await conn.execute(
                "SELECT * FROM appointments WHERE user_id = ? AND is_active = 1",
                (user_id,),
            )
            row = await cursor.fetchone()
            return dict(row) if row else None

    async def get_appointment_by_id(
        self, appointment_id: int
    ) -> dict[str, Any] | None:
        """Получить запись по ID."""
        async with self._get_connection() as conn:
            cursor = await conn.execute(
                "SELECT * FROM appointments WHERE id = ?", (appointment_id,)
            )
            row = await cursor.fetchone()
            return dict(row) if row else None

    async def create_appointment(
        self, user_id: int, user_name: str, phone: str, slot_id: int
    ) -> dict[str, Any] | None:
        """
        Создать запись пользователя.
        Защита от конкурентности и повторной записи одного пользователя.
        Возвращает данные записи или None в случае неудачи.
        """
        async with self._get_connection() as conn:
            # 1. Проверяем, нет ли уже активной записи у пользователя
            cursor = await conn.execute(
                "SELECT id FROM appointments WHERE user_id = ? AND is_active = 1",
                (user_id,),
            )
            if await cursor.fetchone():
                return None

            # 2. Получаем слот и проверяем, свободен ли он
            cursor = await conn.execute(
                "SELECT * FROM slots WHERE id = ? AND is_booked = 0", (slot_id,)
            )
            slot = await cursor.fetchone()
            if not slot:
                return None

            date_str = slot["date"]
            time_str = slot["time"]

            # 3. Атомарно помечаем слот как забронированный
            update_cursor = await conn.execute(
                "UPDATE slots SET is_booked = 1 WHERE id = ? AND is_booked = 0",
                (slot_id,),
            )
            if update_cursor.rowcount == 0:
                return None

            # 4. Добавляем запись
            created_at = datetime.datetime.now().isoformat()
            ins_cursor = await conn.execute(
                """
                INSERT INTO appointments
                (user_id, user_name, phone, date, time, slot_id, is_active, reminder_sent, created_at)
                VALUES (?, ?, ?, ?, ?, ?, 1, 0, ?)
                """,
                (user_id, user_name, phone, date_str, time_str, slot_id, created_at),
            )
            appointment_id = ins_cursor.lastrowid
            await conn.commit()

            return {
                "id": appointment_id,
                "user_id": user_id,
                "user_name": user_name,
                "phone": phone,
                "date": date_str,
                "time": time_str,
                "slot_id": slot_id,
                "is_active": 1,
                "reminder_sent": 0,
                "created_at": created_at,
            }

    async def cancel_appointment_by_user(
        self, user_id: int
    ) -> dict[str, Any] | None:
        """Отменить активную запись пользователя и освободить слот."""
        async with self._get_connection() as conn:
            cursor = await conn.execute(
                "SELECT * FROM appointments WHERE user_id = ? AND is_active = 1",
                (user_id,),
            )
            apt = await cursor.fetchone()
            if not apt:
                return None

            apt_dict = dict(apt)
            # Деактивируем запись
            await conn.execute(
                "UPDATE appointments SET is_active = 0 WHERE id = ?",
                (apt_dict["id"],),
            )
            # Освобождаем слот
            await conn.execute(
                "UPDATE slots SET is_booked = 0 WHERE id = ?",
                (apt_dict["slot_id"],),
            )
            await conn.commit()
            return apt_dict

    async def cancel_appointment_by_id(
        self, appointment_id: int
    ) -> dict[str, Any] | None:
        """Отменить запись по ID (для администратора) и освободить слот."""
        async with self._get_connection() as conn:
            cursor = await conn.execute(
                "SELECT * FROM appointments WHERE id = ? AND is_active = 1",
                (appointment_id,),
            )
            apt = await cursor.fetchone()
            if not apt:
                return None

            apt_dict = dict(apt)
            await conn.execute(
                "UPDATE appointments SET is_active = 0 WHERE id = ?",
                (appointment_id,),
            )
            await conn.execute(
                "UPDATE slots SET is_booked = 0 WHERE id = ?",
                (apt_dict["slot_id"],),
            )
            await conn.commit()
            return apt_dict

    async def get_appointments_for_date(
        self, date_str: str
    ) -> list[dict[str, Any]]:
        """Получить все активные записи на указанную дату."""
        async with self._get_connection() as conn:
            cursor = await conn.execute(
                "SELECT * FROM appointments WHERE date = ? AND is_active = 1 ORDER BY time ASC",
                (date_str,),
            )
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]

    async def get_active_appointments_for_reminders(self) -> list[dict[str, Any]]:
        """Получить все активные записи, по которым еще не отправлено напоминание."""
        async with self._get_connection() as conn:
            cursor = await conn.execute(
                "SELECT * FROM appointments WHERE is_active = 1 AND reminder_sent = 0"
            )
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]

    async def mark_reminder_sent(self, appointment_id: int) -> None:
        """Отметить, что напоминание клиенту отправлено."""
        async with self._get_connection() as conn:
            await conn.execute(
                "UPDATE appointments SET reminder_sent = 1 WHERE id = ?",
                (appointment_id,),
            )
            await conn.commit()


# Глобальный экземпляр базы данных
db = Database()
