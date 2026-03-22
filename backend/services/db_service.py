"""
Database service for NomadIQ.

Uses SQLite for local development (zero setup, free).
Stores trip plans, statuses, outputs, and chat messages.
"""

import os
import json
import aiosqlite
from datetime import datetime, timezone
from typing import Optional, Dict, Any
from loguru import logger

# SQLite database file path
DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "nomadiq.db")


async def initialize_db() -> None:
    """Create database tables if they don't exist."""
    logger.info(f"Initializing SQLite database at: {DB_PATH}")
    async with aiosqlite.connect(DB_PATH) as db:
        await db.executescript("""
            CREATE TABLE IF NOT EXISTS trip_plans (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                destination TEXT NOT NULL,
                starting_location TEXT DEFAULT '',
                travel_dates_start TEXT DEFAULT '',
                travel_dates_end TEXT DEFAULT '',
                duration INTEGER DEFAULT 3,
                traveling_with TEXT DEFAULT 'Solo',
                adults INTEGER DEFAULT 1,
                children INTEGER DEFAULT 0,
                budget REAL DEFAULT 1000,
                budget_currency TEXT DEFAULT 'USD',
                travel_style TEXT DEFAULT 'comfort',
                vibes TEXT DEFAULT '[]',
                interests TEXT DEFAULT '',
                additional_info TEXT DEFAULT '',
                user_id TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS trip_plan_status (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                trip_plan_id TEXT NOT NULL UNIQUE,
                status TEXT NOT NULL DEFAULT 'pending',
                current_step TEXT,
                error TEXT,
                started_at TEXT,
                completed_at TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                FOREIGN KEY (trip_plan_id) REFERENCES trip_plans(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS trip_plan_output (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                trip_plan_id TEXT NOT NULL UNIQUE,
                itinerary TEXT NOT NULL,
                summary TEXT DEFAULT '',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                FOREIGN KEY (trip_plan_id) REFERENCES trip_plans(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS chat_messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                trip_plan_id TEXT NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY (trip_plan_id) REFERENCES trip_plans(id) ON DELETE CASCADE
            );
        """)
        await db.commit()
    logger.info("Database initialized successfully")


async def create_trip_plan(trip_plan_id: str, data: Dict[str, Any]) -> None:
    """Insert a new trip plan record."""
    now = datetime.now(timezone.utc).isoformat()
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """INSERT INTO trip_plans
               (id, name, destination, starting_location,
                travel_dates_start, travel_dates_end, duration,
                traveling_with, adults, children,
                budget, budget_currency, travel_style,
                vibes, interests, additional_info,
                created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                trip_plan_id,
                data.get("name", ""),
                data.get("destination", ""),
                data.get("starting_location", ""),
                data.get("travel_dates", {}).get("start", ""),
                data.get("travel_dates", {}).get("end", ""),
                data.get("duration", 3),
                data.get("traveling_with", "Solo"),
                data.get("adults", 1),
                data.get("children", 0),
                data.get("budget", 1000),
                data.get("budget_currency", "USD"),
                data.get("travel_style", "comfort"),
                json.dumps(data.get("vibes", [])),
                data.get("interests", ""),
                data.get("additional_info", ""),
                now, now,
            ),
        )
        # Create initial status
        await db.execute(
            """INSERT INTO trip_plan_status
               (trip_plan_id, status, current_step, created_at, updated_at)
               VALUES (?, 'pending', 'Queued for processing', ?, ?)""",
            (trip_plan_id, now, now),
        )
        await db.commit()


async def update_plan_status(
    trip_plan_id: str,
    status: str,
    current_step: Optional[str] = None,
    error: Optional[str] = None,
) -> None:
    """Update the status of a trip plan."""
    now = datetime.now(timezone.utc).isoformat()
    async with aiosqlite.connect(DB_PATH) as db:
        if status == "processing" and current_step:
            await db.execute(
                """UPDATE trip_plan_status
                   SET status = ?, current_step = ?, started_at = COALESCE(started_at, ?), updated_at = ?
                   WHERE trip_plan_id = ?""",
                (status, current_step, now, now, trip_plan_id),
            )
        elif status in ("completed", "failed"):
            await db.execute(
                """UPDATE trip_plan_status
                   SET status = ?, current_step = ?, error = ?, completed_at = ?, updated_at = ?
                   WHERE trip_plan_id = ?""",
                (status, current_step, error, now, now, trip_plan_id),
            )
        else:
            await db.execute(
                """UPDATE trip_plan_status
                   SET status = ?, current_step = ?, updated_at = ?
                   WHERE trip_plan_id = ?""",
                (status, current_step, now, trip_plan_id),
            )
        await db.commit()


async def save_plan_output(trip_plan_id: str, itinerary_json: str, summary: str = "") -> None:
    """Save the generated itinerary output."""
    now = datetime.now(timezone.utc).isoformat()
    async with aiosqlite.connect(DB_PATH) as db:
        # Delete existing output if any
        await db.execute("DELETE FROM trip_plan_output WHERE trip_plan_id = ?", (trip_plan_id,))
        await db.execute(
            """INSERT INTO trip_plan_output
               (trip_plan_id, itinerary, summary, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?)""",
            (trip_plan_id, itinerary_json, summary, now, now),
        )
        await db.commit()


async def get_plan_status(trip_plan_id: str) -> Optional[Dict[str, Any]]:
    """Get the current status of a trip plan."""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            """SELECT tp.*, tps.status, tps.current_step, tps.error,
                      tps.started_at, tps.completed_at,
                      tpo.itinerary
               FROM trip_plans tp
               LEFT JOIN trip_plan_status tps ON tp.id = tps.trip_plan_id
               LEFT JOIN trip_plan_output tpo ON tp.id = tpo.trip_plan_id
               WHERE tp.id = ?""",
            (trip_plan_id,),
        )
        row = await cursor.fetchone()
        if row:
            return dict(row)
        return None


async def get_all_plans() -> list:
    """Get all trip plans with their statuses."""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            """SELECT tp.id, tp.name, tp.destination, tp.duration,
                      tp.created_at, tps.status, tps.current_step
               FROM trip_plans tp
               LEFT JOIN trip_plan_status tps ON tp.id = tps.trip_plan_id
               ORDER BY tp.created_at DESC"""
        )
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]


async def save_chat_message(trip_plan_id: str, role: str, content: str) -> None:
    """Save a chat message."""
    now = datetime.now(timezone.utc).isoformat()
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """INSERT INTO chat_messages (trip_plan_id, role, content, created_at)
               VALUES (?, ?, ?, ?)""",
            (trip_plan_id, role, content, now),
        )
        await db.commit()


async def get_chat_history(trip_plan_id: str) -> list:
    """Get chat history for a trip plan."""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            """SELECT role, content, created_at
               FROM chat_messages
               WHERE trip_plan_id = ?
               ORDER BY created_at ASC""",
            (trip_plan_id,),
        )
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]


async def update_plan_output(trip_plan_id: str, itinerary_json: str) -> None:
    """Update an existing plan output (used by chat modifications)."""
    now = datetime.now(timezone.utc).isoformat()
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """UPDATE trip_plan_output SET itinerary = ?, updated_at = ?
               WHERE trip_plan_id = ?""",
            (itinerary_json, now, trip_plan_id),
        )
        await db.commit()
