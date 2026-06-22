from __future__ import annotations
"""
Database Manager — PostgreSQL async (asyncpg)
Thay thế hoàn toàn SQLite/aiosqlite.
Toàn bộ API công khai (get_tu_si, update_tu_si, ...) giữ nguyên —
không cần sửa bất kỳ file cogs nào.

Cài đặt:
    pip install asyncpg

Biến môi trường Railway (tự tạo khi add PostgreSQL plugin):
    DATABASE_URL=postgresql://user:pass@host:port/dbname
"""

import logging
import asyncio
import json
import time
import os
import importlib
from typing import Any

log = logging.getLogger("database")

# ══════════════════════════════════════════════════════
#  CONNECTION POOL
# ══════════════════════════════════════════════════════
try:
    asyncpg = importlib.import_module("asyncpg")
except ModuleNotFoundError as e:
    raise ImportError("Thiếu asyncpg! Chạy: pip install asyncpg") from e

_pool: Any = None
_write_queue: asyncio.Queue = asyncio.Queue()
_worker_task: asyncio.Task | None = None


async def get_pool() -> Any:
    global _pool
    if _pool is None:
        url = os.environ.get("DATABASE_URL")
        if not url:
            raise RuntimeError("Thiếu biến môi trường DATABASE_URL!")
        async def _init_conn(conn):
            # Đăng ký codec cho int8 (BIGINT) để asyncpg không nhầm sang int4
            await conn.set_type_codec(
                'int8', schema='pg_catalog',
                encoder=lambda v: str(v),
                decoder=lambda v: int(v),
                format='text',
            )

        _pool = await asyncpg.create_pool(
            url,
            min_size=2,
            max_size=10,
            statement_cache_size=0,   # bắt buộc với Railway pgBouncer
            command_timeout=30,
            init=_init_conn,
        )
        log.info("PostgreSQL pool created")
    return _pool


# ══════════════════════════════════════════════════════
#  WRITE QUEUE (giữ nguyên pattern fire-and-forget)
# ══════════════════════════════════════════════════════

async def _write_worker():
    """Worker chạy background, xử lý tất cả writes tuần tự."""
    pool = await get_pool()
    while True:
        try:
            item = await asyncio.wait_for(_write_queue.get(), timeout=1.0)
            if item is None:
                _write_queue.task_done()
                break
            sql, params, future = item
            try:
                async with pool.acquire() as conn:
                    # Dùng fetchrow để tránh asyncpg tự suy luận kiểu int32
                    # Ép tất cả int params thành Python int (không để asyncpg đoán int32)
                    safe_params = tuple(
                        int(p) if isinstance(p, (int, float)) and not isinstance(p, bool) else p
                        for p in params
                    )
                    result = await conn.execute(sql, *safe_params)
                    lastrowid = None
                    if future and not future.done():
                        future.set_result(lastrowid)
            except Exception as e:
                if future and not future.done():
                    future.set_exception(e)
                else:
                    log.error(f"DB write error (fire-forget): {e}")
            finally:
                _write_queue.task_done()
        except asyncio.TimeoutError:
            continue
        except asyncio.CancelledError:
            break
        except Exception as e:
            log.error(f"DB worker error: {e}")


def _enqueue(sql: str, params: tuple = (), *, wait: bool = False):
    """
    Đẩy write vào queue.
    wait=False → fire-and-forget
    wait=True  → trả về Future
    """
    loop = asyncio.get_running_loop()
    future = loop.create_future() if wait else None
    _write_queue.put_nowait((sql, params, future))
    return future


async def start_worker():
    global _worker_task
    if _worker_task is None or _worker_task.done():
        _worker_task = asyncio.create_task(_write_worker())


async def close_db():
    global _pool
    if _worker_task and not _worker_task.done():
        _write_queue.put_nowait(None)
        try:
            await asyncio.wait_for(_worker_task, timeout=10.0)
        except (asyncio.TimeoutError, asyncio.CancelledError):
            _worker_task.cancel()
            try:
                await _worker_task
            except asyncio.CancelledError:
                pass
    if _pool:
        await _pool.close()
        _pool = None
        log.info("PostgreSQL pool closed")


# ══════════════════════════════════════════════════════
#  SCHEMA — PostgreSQL syntax
# ══════════════════════════════════════════════════════
SCHEMA = """
CREATE TABLE IF NOT EXISTS tu_si (
    user_id             BIGINT PRIMARY KEY,
    dao_hieu            TEXT    DEFAULT 'Vô Danh',
    linh_can            INTEGER DEFAULT 4,
    linh_can_phu        TEXT    DEFAULT '[]',
    canh_gioi           INTEGER DEFAULT 0,
    cap_nho             INTEGER DEFAULT 1,
    exp                 INTEGER DEFAULT 0,
    hp                  INTEGER DEFAULT 100,
    hp_max              INTEGER DEFAULT 100,
    cong                INTEGER DEFAULT 10,
    thu                 INTEGER DEFAULT 5,
    linh_thach          BIGINT  DEFAULT 0,
    tong_mon            INTEGER DEFAULT -1,
    phap_bao            TEXT    DEFAULT '[]',
    phap_bao_active     INTEGER DEFAULT -1,
    yeu_thu             TEXT    DEFAULT '[]',
    yeu_thu_active      INTEGER DEFAULT -1,
    sung_thu            TEXT    DEFAULT '{}',
    sung_thu_active     INTEGER DEFAULT -1,
    dan_duoc            TEXT    DEFAULT '{}',
    nguyen_lieu         TEXT    DEFAULT '{}',
    thang_pvp           INTEGER DEFAULT 0,
    thua_pvp            INTEGER DEFAULT 0,
    ngay_tao            BIGINT  DEFAULT 0,
    cd_tu_luyen         BIGINT  DEFAULT 0,
    cd_dot_pha          BIGINT  DEFAULT 0,
    cd_khai_hoang       BIGINT  DEFAULT 0,
    cd_bi_canh          BIGINT  DEFAULT 0,
    cd_diem_danh        BIGINT  DEFAULT 0,
    chuoi_diem_danh     INTEGER DEFAULT 0,
    tong_tu_luyen       INTEGER DEFAULT 0,
    danh_hieu_hien      TEXT    DEFAULT '',
    gioi_tinh           TEXT    DEFAULT '',
    tuoi                INTEGER DEFAULT 0,
    so_thich            TEXT    DEFAULT '',
    the_luc             INTEGER DEFAULT 250,
    the_luc_cap_nhat    BIGINT  DEFAULT 0,
    tran_the_luc        INTEGER DEFAULT 0,
    tran_the_luc_cap_nhat BIGINT  DEFAULT 0,
    cong_phap_so_huu    TEXT    DEFAULT '[]',
    cong_phap_trang_bi  TEXT    DEFAULT '{}',
    cong_phap_tang      TEXT    DEFAULT '{}',
    cong_phap_hoc       TEXT    DEFAULT '[]',
    cong_phap_active    INTEGER DEFAULT -1,
    bc_thua_lan_truoc   INTEGER DEFAULT 0,
    tong_tu_vi          BIGINT  DEFAULT 0,
    linh_luc            INTEGER DEFAULT 0,
    hoi_tam             INTEGER DEFAULT 0,
    ho_tam              INTEGER DEFAULT 0,
    bao_kich            INTEGER DEFAULT 0,
    khang_bao           INTEGER DEFAULT 0,
    banner_id           INTEGER DEFAULT 0,
    the_chat            TEXT    DEFAULT '',
    linh_can_so_huu     TEXT    DEFAULT '[]',
    linh_can_diem       TEXT    DEFAULT '{}',
    manh_linh_can       TEXT    DEFAULT '{}',
    linh_qua            TEXT    DEFAULT '{}',
    dotpha_tc_nl        TEXT    DEFAULT '{}',
    linh_can_lop2       TEXT    DEFAULT '{}',
    so_lan_trung_sinh   INTEGER DEFAULT 0,
    ti_le_van_dinh      REAL    DEFAULT 0.01,
    van_dinh_all_stat_pct REAL  DEFAULT 0,
    da_van_dinh         BOOLEAN DEFAULT FALSE,
    y_canh              TEXT    DEFAULT '{}',
    tran_dao_active     TEXT    DEFAULT ''
);

CREATE TABLE IF NOT EXISTS tong_mon_thanh_vien (
    tong_mon_id BIGINT,
    user_id     BIGINT,
    chuc_vu     TEXT DEFAULT 'Môn Đồ',
    PRIMARY KEY (tong_mon_id, user_id)
);

CREATE TABLE IF NOT EXISTS phien_cho (
    id          BIGSERIAL PRIMARY KEY,
    nguoi_ban   BIGINT,
    loai        TEXT,
    item_id     INTEGER,
    item_key    TEXT DEFAULT '',
    so_luong    INTEGER DEFAULT 1,
    gia         BIGINT,
    thoi_gian   BIGINT,
    da_ban      INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS boss_state (
    boss_id         INTEGER PRIMARY KEY,
    hp_hien         BIGINT,
    spawn_time      BIGINT,
    nguoi_tan_cong  TEXT DEFAULT '{}',
    canh_gioi       INTEGER DEFAULT 3,
    message_id      BIGINT DEFAULT 0,
    channel_id      BIGINT DEFAULT 0,
    end_time        BIGINT DEFAULT 0
);

CREATE TABLE IF NOT EXISTS boss_tham_gia (
    boss_id     INTEGER,
    user_id     BIGINT,
    spawn_time  BIGINT  DEFAULT 0,
    tong_damage BIGINT  DEFAULT 0,
    da_nhan     INTEGER DEFAULT 0,
    PRIMARY KEY (boss_id, user_id, spawn_time)
);

CREATE TABLE IF NOT EXISTS boss_ended_spawns (
    boss_id     INTEGER,
    spawn_time  BIGINT,
    end_time    BIGINT  DEFAULT 0,
    PRIMARY KEY (boss_id, spawn_time)
);

CREATE TABLE IF NOT EXISTS quan_he (
    user_a      BIGINT,
    user_b      BIGINT,
    diem        INTEGER DEFAULT 0,
    loai        TEXT    DEFAULT '',
    ngay_tao    BIGINT  DEFAULT 0,
    PRIMARY KEY (user_a, user_b)
);

CREATE TABLE IF NOT EXISTS tang_qua_log (
    user_id     BIGINT,
    target_id   BIGINT,
    ngay        TEXT,
    diem_tang   INTEGER DEFAULT 0,
    PRIMARY KEY (user_id, target_id, ngay)
);

CREATE TABLE IF NOT EXISTS giao_dich_log (
    id          BIGSERIAL PRIMARY KEY,
    loai        TEXT,        -- 'phien_cho' | 'tang_lt' | 'tang_dan' | 'private_trade'
    sender_id   BIGINT,      -- người gửi/bán
    receiver_id BIGINT,      -- người nhận/mua
    item_name   TEXT DEFAULT '',
    item_loai   TEXT DEFAULT '',   -- 'Linh Quả' | 'Mảnh Linh Căn' | 'Đan Dược' | ...
    item_key    TEXT DEFAULT '',   -- lq_id / nl_id / dan id
    so_luong    INTEGER DEFAULT 1,
    gia_lt      BIGINT  DEFAULT 0,   -- LT thực tế chuyển tay
    thoi_gian   BIGINT  DEFAULT 0,
    ghi_chu     TEXT    DEFAULT ''   -- thêm context nếu cần
);
CREATE INDEX IF NOT EXISTS idx_gdlog_sender   ON giao_dich_log(sender_id);
CREATE INDEX IF NOT EXISTS idx_gdlog_receiver ON giao_dich_log(receiver_id);
CREATE INDEX IF NOT EXISTS idx_gdlog_time     ON giao_dich_log(thoi_gian);

CREATE TABLE IF NOT EXISTS boss_guild_messages (
    boss_id    INTEGER NOT NULL,
    guild_id   BIGINT  NOT NULL,
    msg_id     BIGINT  DEFAULT 0,
    channel_id BIGINT  DEFAULT 0,
    PRIMARY KEY (boss_id, guild_id)
);

CREATE TABLE IF NOT EXISTS guild_config (
    guild_id        BIGINT PRIMARY KEY,
    boss_channel_id BIGINT DEFAULT 0,
    boss_msg_id     BIGINT DEFAULT 0
);

CREATE TABLE IF NOT EXISTS reset_log (
    user_id      BIGINT PRIMARY KEY,
    so_lan_reset INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS world_chat_channels (
    guild_id    BIGINT  PRIMARY KEY,
    channel_id  BIGINT  NOT NULL,
    webhook_url TEXT    NOT NULL,
    active      INTEGER DEFAULT 1,
    created_at  BIGINT  DEFAULT 0,
    thread_id   BIGINT  DEFAULT NULL
);

CREATE TABLE IF NOT EXISTS cross_pvp_challenges (
    id              SERIAL  PRIMARY KEY,
    challenger_id   BIGINT  NOT NULL,
    challenger_guild BIGINT NOT NULL,
    target_id       BIGINT  NOT NULL,
    cuoc_lt         INTEGER DEFAULT 0,
    created_at      BIGINT  NOT NULL,
    status          TEXT    DEFAULT 'pending'
);

CREATE TABLE IF NOT EXISTS active_vote (
    id          INTEGER PRIMARY KEY DEFAULT 1,
    question    TEXT    NOT NULL,
    start_ts    BIGINT  NOT NULL,
    end_ts      BIGINT  NOT NULL,
    votes_json  TEXT    DEFAULT '{}',
    msgs_json   TEXT    DEFAULT '{}'
);

CREATE TABLE IF NOT EXISTS promo_codes (
    code        TEXT    PRIMARY KEY,
    goi         TEXT    NOT NULL,       -- 'dot_pha_tc' | 'ngu_hanh_qua' | 'phap_bao'
    nguoi_tao   BIGINT  DEFAULT 0,
    nguoi_dung  BIGINT  DEFAULT 0,     -- 0 = chưa dùng
    ngay_tao    BIGINT  DEFAULT 0,
    ngay_dung   BIGINT  DEFAULT 0
);
"""


async def migrate_db():
    """Thêm cột mới nếu chưa có (tương thích upgrade từ schema cũ)."""
    pool = await get_pool()

    tu_si_cols = [
        ("danh_hieu_hien",    "TEXT DEFAULT ''"),
        ("gioi_tinh",         "TEXT DEFAULT ''"),
        ("tuoi",              "INTEGER DEFAULT 0"),
        ("so_thich",          "TEXT DEFAULT ''"),
        ("the_luc",           "INTEGER DEFAULT 250"),
        ("the_luc_cap_nhat",  "BIGINT DEFAULT 0"),
        ("cong_phap_so_huu",  "TEXT DEFAULT '[]'"),
        ("cong_phap_trang_bi","TEXT DEFAULT '{}'"),
        ("cong_phap_tang",    "TEXT DEFAULT '{}'"),
        ("cong_phap_hoc",     "TEXT DEFAULT '[]'"),
        ("cong_phap_active",  "INTEGER DEFAULT -1"),
        ("bc_thua_lan_truoc", "INTEGER DEFAULT 0"),
        ("cd_bi_canh",        "BIGINT DEFAULT 0"),
        ("tong_tu_vi",        "BIGINT DEFAULT 0"),
        ("banner_id",         "INTEGER DEFAULT 0"),
        ("cd_dot_pha",        "BIGINT DEFAULT 0"),
        ("linh_can_phu",      "TEXT DEFAULT '[]'"),
        ("linh_luc",          "INTEGER DEFAULT 0"),
        ("hoi_tam",           "INTEGER DEFAULT 0"),
        ("ho_tam",            "INTEGER DEFAULT 0"),
        ("bao_kich",          "INTEGER DEFAULT 0"),
        ("khang_bao",         "INTEGER DEFAULT 0"),
        ("the_chat",          "TEXT DEFAULT ''"),
        ("linh_can_so_huu",   "TEXT DEFAULT '[]'"),
        ("linh_can_diem",     "TEXT DEFAULT '{}'"),
        ("manh_linh_can",     "TEXT DEFAULT '{}'"),
        ("linh_qua",          "TEXT DEFAULT '{}'"),
        ("dotpha_tc_nl",      "TEXT DEFAULT '{}'"),
        ("phap_bao_active",   "INTEGER DEFAULT -1"),
        ("tran_the_luc",       "INTEGER DEFAULT 0"),
        ("tran_the_luc_cap_nhat", "BIGINT DEFAULT 0"),
        ("linh_can_lop2",      "TEXT DEFAULT '{}'"),
        ("so_lan_trung_sinh",  "INTEGER DEFAULT 0"),
        ("ti_le_van_dinh",     "REAL DEFAULT 0.01"),
        ("van_dinh_all_stat_pct", "REAL DEFAULT 0"),
        ("da_van_dinh",        "BOOLEAN DEFAULT FALSE"),
        ("y_canh",             "TEXT DEFAULT '{}'"),
        ("tran_dao_active",    "TEXT DEFAULT ''"),
    ]

    async with pool.acquire() as conn:
        # Lấy danh sách cột hiện tại của tu_si
        existing = {
            row["column_name"]
            for row in await conn.fetch(
                "SELECT column_name FROM information_schema.columns WHERE table_name='tu_si'"
            )
        }
        for col, typedef in tu_si_cols:
            if col not in existing:
                try:
                    await conn.execute(f"ALTER TABLE tu_si ADD COLUMN IF NOT EXISTS {col} {typedef}")
                    log.info(f"DB migration tu_si: +{col}")
                except Exception as e:
                    log.warning(f"DB migration tu_si skip {col}: {e}")

        # Nâng linh_thach từ INTEGER lên BIGINT (tránh overflow khi LT > 2.1 tỷ)
        try:
            await conn.execute("""
                ALTER TABLE tu_si
                ALTER COLUMN linh_thach TYPE BIGINT
            """)
            log.info("DB migration tu_si: linh_thach → BIGINT")
        except Exception as e:
            log.debug(f"DB migration tu_si linh_thach TYPE (ok nếu đã BIGINT): {e}")

        # giao_dich_log table
        try:
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS giao_dich_log (
                    id          BIGSERIAL PRIMARY KEY,
                    loai        TEXT,
                    sender_id   BIGINT,
                    receiver_id BIGINT,
                    item_name   TEXT DEFAULT '',
                    item_loai   TEXT DEFAULT '',
                    item_key    TEXT DEFAULT '',
                    so_luong    INTEGER DEFAULT 1,
                    gia_lt      BIGINT  DEFAULT 0,
                    thoi_gian   BIGINT  DEFAULT 0,
                    ghi_chu     TEXT    DEFAULT ''
                )
            """)
            await conn.execute("CREATE INDEX IF NOT EXISTS idx_gdlog_sender   ON giao_dich_log(sender_id)")
            await conn.execute("CREATE INDEX IF NOT EXISTS idx_gdlog_receiver ON giao_dich_log(receiver_id)")
            await conn.execute("CREATE INDEX IF NOT EXISTS idx_gdlog_time     ON giao_dich_log(thoi_gian)")
            # Add item_loai / item_key if missing (upgrade from old schema)
            gdl_cols = {r["column_name"] for r in await conn.fetch(
                "SELECT column_name FROM information_schema.columns WHERE table_name='giao_dich_log'")}
            if "item_loai" not in gdl_cols:
                await conn.execute("ALTER TABLE giao_dich_log ADD COLUMN IF NOT EXISTS item_loai TEXT DEFAULT ''")
            if "item_key" not in gdl_cols:
                await conn.execute("ALTER TABLE giao_dich_log ADD COLUMN IF NOT EXISTS item_key TEXT DEFAULT ''")
        except Exception as e:
            log.warning(f"DB migration giao_dich_log: {e}")

        # phien_cho: item_key
        pc_cols = {
            row["column_name"]
            for row in await conn.fetch(
                "SELECT column_name FROM information_schema.columns WHERE table_name='phien_cho'"
            )
        }
        if "item_key" not in pc_cols:
            try:
                await conn.execute("ALTER TABLE phien_cho ADD COLUMN IF NOT EXISTS item_key TEXT DEFAULT ''")
                log.info("DB migration phien_cho: +item_key")
            except Exception as e:
                log.warning(f"DB migration phien_cho skip item_key: {e}")

        # boss_ended_spawns
        try:
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS boss_ended_spawns (
                    boss_id     INTEGER,
                    spawn_time  BIGINT,
                    end_time    BIGINT DEFAULT 0,
                    PRIMARY KEY (boss_id, spawn_time)
                )
            """)
        except Exception as e:
            log.warning(f"DB migration boss_ended_spawns: {e}")

        # boss_tham_gia: da_nhan
        btj_cols = {
            row["column_name"]
            for row in await conn.fetch(
                "SELECT column_name FROM information_schema.columns WHERE table_name='boss_tham_gia'"
            )
        }
        if "da_nhan" not in btj_cols:
            try:
                await conn.execute("ALTER TABLE boss_tham_gia ADD COLUMN IF NOT EXISTS da_nhan INTEGER DEFAULT 0")
                log.info("DB migration boss_tham_gia: +da_nhan")
            except Exception as e:
                log.warning(f"DB migration boss_tham_gia skip da_nhan: {e}")

        # boss_state: các cột mới
        bs_cols = {
            row["column_name"]
            for row in await conn.fetch(
                "SELECT column_name FROM information_schema.columns WHERE table_name='boss_state'"
            )
        }
        for col, typedef in [
            ("canh_gioi",  "INTEGER DEFAULT 3"),
            ("message_id", "BIGINT DEFAULT 0"),
            ("channel_id", "BIGINT DEFAULT 0"),
            ("end_time",   "BIGINT DEFAULT 0"),
        ]:
            if col not in bs_cols:
                try:
                    await conn.execute(f"ALTER TABLE boss_state ADD COLUMN IF NOT EXISTS {col} {typedef}")
                    log.info(f"DB migration boss_state: +{col}")
                except Exception as e:
                    log.warning(f"DB migration boss_state skip {col}: {e}")

        # world_chat_channels table (migration safe)
        try:
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS world_chat_channels (
                    guild_id    BIGINT  PRIMARY KEY,
                    channel_id  BIGINT  NOT NULL,
                    webhook_url TEXT    NOT NULL,
                    active      INTEGER DEFAULT 1,
                    created_at  BIGINT  DEFAULT 0,
                    thread_id   BIGINT  DEFAULT NULL
                )
            """)
            # Add thread_id column if upgrading from older schema
            await conn.execute("""
                ALTER TABLE world_chat_channels
                ADD COLUMN IF NOT EXISTS thread_id BIGINT DEFAULT NULL
            """)
        except Exception as e:
            log.warning(f"DB migration world_chat_channels: {e}")

        # cross_pvp_challenges table (migration safe)
        try:
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS cross_pvp_challenges (
                    id               SERIAL  PRIMARY KEY,
                    challenger_id    BIGINT  NOT NULL,
                    challenger_guild BIGINT  NOT NULL,
                    target_id        BIGINT  NOT NULL,
                    cuoc_lt          INTEGER DEFAULT 0,
                    created_at       BIGINT  NOT NULL,
                    status           TEXT    DEFAULT 'pending'
                )
            """)
        except Exception as e:
            log.warning(f"DB migration cross_pvp_challenges: {e}")

        # active_vote table (migration safe)
        try:
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS active_vote (
                    id          INTEGER PRIMARY KEY DEFAULT 1,
                    question    TEXT    NOT NULL,
                    start_ts    BIGINT  NOT NULL,
                    end_ts      BIGINT  NOT NULL,
                    votes_json  TEXT    DEFAULT '{}',
                    msgs_json   TEXT    DEFAULT '{}'
                )
            """)
        except Exception as e:
            log.warning(f"DB migration active_vote: {e}")

        # promo_codes table (migration safe)
        try:
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS promo_codes (
                    code        TEXT    PRIMARY KEY,
                    goi         TEXT    NOT NULL,
                    nguoi_tao   BIGINT  DEFAULT 0,
                    nguoi_dung  BIGINT  DEFAULT 0,
                    ngay_tao    BIGINT  DEFAULT 0,
                    ngay_dung   BIGINT  DEFAULT 0
                )
            """)
        except Exception as e:
            log.warning(f"DB migration promo_codes: {e}")

    log.info("DB migration complete")


async def migrate_linh_can_lop2():
    """Migration: tái tạo linh_can_lop2 cho tất cả user dựa trên canh_gioi hiện tại.
    Logic: lop2_expected[field] = canh_gioi × Σ(dot_pha_buff[field]) của tất cả linh căn đang sở hữu.
    Nếu giá trị hiện tại THẤP HƠN kỳ vọng → cập nhật lên đúng (fix user bị thiếu do migration cũ bỏ qua).
    Nếu giá trị hiện tại CAO HƠN → giữ nguyên (tôn trọng tích lũy thực tế).
    """
    from utils.config import LINH_CAN_BY_ID as _LC_BY_ID
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            "SELECT user_id, canh_gioi, linh_can_so_huu, linh_can_lop2 FROM tu_si "
            "WHERE canh_gioi > 0"
        )
        updated = 0
        for row in rows:
            cg     = row["canh_gioi"]
            lc_raw = row["linh_can_so_huu"]
            lc_ids = json.loads(lc_raw) if isinstance(lc_raw, str) else (lc_raw or [])
            if not lc_ids:
                continue

            # Tính giá trị kỳ vọng dựa trên canh_gioi × buff mỗi linh căn
            lop2_expected = {}
            for lc_id in lc_ids:
                lc = _LC_BY_ID.get(lc_id)
                if not lc:
                    continue
                dpb = lc.get("dot_pha_buff", {})
                for fk in ("hoi_tam", "ho_tam", "bao_kich", "khang_bao", "drop_rate", "exp_pct"):
                    if dpb.get(fk):
                        lop2_expected[fk] = round(lop2_expected.get(fk, 0) + dpb[fk] * cg, 4)

            if not lop2_expected:
                continue

            # Đọc giá trị hiện tại
            lop2_raw = row["linh_can_lop2"]
            try:
                lop2_cur = json.loads(lop2_raw) if isinstance(lop2_raw, str) else (lop2_raw or {})
                if not isinstance(lop2_cur, dict):
                    lop2_cur = {}
            except Exception:
                lop2_cur = {}

            # Lấy MAX giữa hiện tại và kỳ vọng cho từng field
            lop2_fixed = dict(lop2_cur)
            needs_update = False
            for fk, expected_val in lop2_expected.items():
                cur_val = lop2_cur.get(fk, 0)
                if cur_val < expected_val - 0.001:  # dùng epsilon tránh float imprecision
                    lop2_fixed[fk] = expected_val
                    needs_update = True

            if needs_update:
                await conn.execute(
                    "UPDATE tu_si SET linh_can_lop2=$1 WHERE user_id=$2",
                    json.dumps(lop2_fixed, ensure_ascii=False), row["user_id"]
                )
                updated += 1
        log.info(f"[MigrateLop2] Đã fix linh_can_lop2 cho {updated}/{len(rows)} user")
    return updated


async def init_db():
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute(SCHEMA)
    await migrate_db()
    await migrate_linh_can_lop2()   # one-time migration: reconstruct linh_can_lop2 for existing users
    await start_worker()
    log.info("DB + write worker ready (PostgreSQL)")


# ══════════════════════════════════════════════════════
#  HELPERS
# ══════════════════════════════════════════════════════
def _parse(row: dict) -> dict:
    for key in ["phap_bao", "yeu_thu", "nguyen_lieu", "cong_phap_so_huu", "linh_can_phu",
                "linh_can_so_huu", "cong_phap_hoc"]:
        if key not in row:
            continue
        val = row[key]
        if isinstance(val, str):
            row[key] = json.loads(val or "[]")
        elif not isinstance(val, list):
            row[key] = []  # int/None/kiểu lạ → reset list rỗng
    if "phap_bao_active" in row and row["phap_bao_active"] is not None:
        row["phap_bao_active"] = int(row["phap_bao_active"])
    for key in ["dan_duoc", "cong_phap_trang_bi", "cong_phap_tang", "sung_thu",
                "linh_can_diem", "manh_linh_can", "linh_qua", "dotpha_tc_nl", "linh_can_lop2"]:
        if key not in row:
            continue
        val = row[key]
        if isinstance(val, str):
            row[key] = json.loads(val or "{}")
        elif not isinstance(val, dict):
            row[key] = {}  # int/None/kiểu lạ → reset dict rỗng
    return row


def _serialize(kwargs: dict) -> dict:
    for key in ["phap_bao", "yeu_thu", "cong_phap_so_huu", "linh_can_phu", "linh_can_so_huu"]:
        if key in kwargs and not isinstance(kwargs[key], str):
            kwargs[key] = json.dumps(kwargs[key], ensure_ascii=False)
    for key in ["dan_duoc", "nguyen_lieu", "cong_phap_trang_bi", "cong_phap_tang", "sung_thu",
                "cong_phap_hoc", "linh_can_diem", "manh_linh_can", "linh_qua", "dotpha_tc_nl",
                "linh_can_lop2"]:
        if key in kwargs and not isinstance(kwargs[key], str):
            kwargs[key] = json.dumps(kwargs[key], ensure_ascii=False)
    return kwargs


# ── Thể lực ────────────────────────────────────────────
THE_LUC_BASE    = 250       # Tăng từ 200 → 250
THE_LUC_PER_CG  = 20
THE_LUC_HOI     = 60        # 1 phút / điểm (thể lực chính)
THE_LUC_MAX     = THE_LUC_BASE

TRAN_THE_LUC_MAX = 100      # Tràn thể lực tối đa
TRAN_THE_LUC_HOI = 240      # 4 phút / điểm (thể lực tràn)


def the_luc_toi_da(canh_gioi: int) -> int:
    return THE_LUC_BASE + canh_gioi * THE_LUC_PER_CG


def get_the_luc(ts: dict) -> int:
    """Tính thể lực chính hiện tại (hồi N giây/điểm, tối đa 250+CG×20).
    Ý Cảnh 'Sinh Cơ Vô Tận' giảm thời gian hồi mỗi điểm."""
    import time as _time
    from utils.config import Y_CANH_ALL_NODES
    cg = ts.get("canh_gioi", 0)
    tl_max = the_luc_toi_da(cg)
    tl = ts.get("the_luc", tl_max)
    cap_nhat = ts.get("the_luc_cap_nhat", 0)
    if tl >= tl_max:
        return tl_max
    elapsed = int(_time.time()) - cap_nhat
    # Ý Cảnh: the_luc_hoi giảm giây hồi mỗi điểm
    hoi_giam = 0
    raw_yc = ts.get("y_canh", {})
    if isinstance(raw_yc, dict) and raw_yc:
        for nid, lv in raw_yc.items():
            if lv <= 0:
                continue
            nd_cfg = Y_CANH_ALL_NODES.get(nid)
            if nd_cfg and "the_luc_hoi" in nd_cfg.get("effect", {}):
                hoi_giam += nd_cfg["effect"]["the_luc_hoi"] * lv
    hoi_interval = max(10, THE_LUC_HOI - hoi_giam)
    hoi = elapsed // hoi_interval
    return min(tl_max, tl + hoi)


def get_tran_the_luc(ts: dict) -> int:
    """Tính thể lực tràn hiện tại (hồi 4 phút/điểm, tối đa 100).
    Chỉ tích lũy khi thanh thể lực chính đã đầy.

    Fix: Tránh tính elapsed time bao gồm thời gian khi chính chưa đầy.
    Thay vì dùng tran_the_luc_cap_nhat (có thể rất cũ), ta tính thời điểm
    chính vừa đạt đầy rồi lấy max với cap_nhat để chỉ tính khoảng thời gian
    thực sự hợp lệ.
    """
    import time as _time
    now      = int(_time.time())
    tl_raw   = ts.get("the_luc", the_luc_toi_da(ts.get("canh_gioi", 0)))
    tl_max   = the_luc_toi_da(ts.get("canh_gioi", 0))
    tl_cap_nhat = ts.get("the_luc_cap_nhat", 0)

    # Thời điểm chính đạt đầy (có thể trong quá khứ nếu tl_raw < tl_max)
    if tl_raw >= tl_max:
        # Đã đầy tại lúc lưu → chính đầy ngay tại tl_cap_nhat
        chinh_day_luc = tl_cap_nhat
    else:
        # Chính chưa đầy → tính thêm bao lâu nữa mới đầy
        can_them = tl_max - tl_raw
        chinh_day_luc = tl_cap_nhat + can_them * THE_LUC_HOI
        if chinh_day_luc > now:
            # Chính vẫn chưa đầy hiện tại → tràn không hồi
            return min(TRAN_THE_LUC_MAX, ts.get("tran_the_luc", 0))

    tran     = ts.get("tran_the_luc", 0)
    cap_nhat = ts.get("tran_the_luc_cap_nhat", 0)
    if tran >= TRAN_THE_LUC_MAX:
        return TRAN_THE_LUC_MAX

    # Chỉ tính elapsed từ lúc chính ĐẦY hoặc cap_nhat (lấy cái muộn hơn)
    valid_from = max(cap_nhat, chinh_day_luc)
    elapsed = max(0, now - valid_from)
    hoi = elapsed // TRAN_THE_LUC_HOI
    return min(TRAN_THE_LUC_MAX, tran + hoi)


# ══════════════════════════════════════════════════════
#  TU SĨ
# ══════════════════════════════════════════════════════
async def get_tu_si(user_id: int) -> dict | None:
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow("SELECT * FROM tu_si WHERE user_id=$1", user_id)
        return _parse(dict(row)) if row else None


async def create_tu_si(user_id: int, dao_hieu: str, linh_can: int = 0) -> dict:
    from utils.config import hp_max_cong_thuc, cong_cong_thuc, thu_cong_thuc
    hp = hp_max_cong_thuc(0, 1)
    cong = cong_cong_thuc(0, 1)
    thu = thu_cong_thuc(0, 1)
    now = int(time.time())
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            """INSERT INTO tu_si (user_id, dao_hieu, hp, hp_max, cong, thu, ngay_tao)
               VALUES ($1, $2, $3, $4, $5, $6, $7)
               ON CONFLICT (user_id) DO NOTHING""",
            user_id, dao_hieu, hp, hp, cong, thu, now
        )
    return await get_tu_si(user_id)


async def update_tu_si(user_id: int, **kwargs):
    """Fire-and-forget."""
    kwargs = _serialize(kwargs)
    cols = ", ".join(f"{k}=${i+2}" for i, k in enumerate(kwargs))
    vals = tuple(kwargs.values())
    sql = f"UPDATE tu_si SET {cols} WHERE user_id=$1"
    # Ép int thành Python int để tránh asyncpg nhầm int32 vs int64
    safe = tuple(int(v) if isinstance(v, int) else v for v in (user_id,) + vals)
    _enqueue(sql, safe)


async def update_tu_si_wait(user_id: int, **kwargs):
    """Chờ write xong."""
    kwargs = _serialize(kwargs)
    vals = tuple(kwargs.values())
    placeholders = ", ".join(f"{k}=${i+2}" for i, k in enumerate(kwargs))
    sql = f"UPDATE tu_si SET {placeholders} WHERE user_id=$1"
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute(sql, user_id, *vals)


async def delete_tu_si(user_id: int):
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute("DELETE FROM tu_si WHERE user_id=$1", user_id)
        await conn.execute("DELETE FROM boss_tham_gia WHERE user_id=$1", user_id)
        await conn.execute("DELETE FROM quan_he WHERE user_a=$1 OR user_b=$1", user_id)
        await conn.execute("DELETE FROM tang_qua_log WHERE user_id=$1 OR target_id=$1", user_id)
        await conn.execute("DELETE FROM phien_cho WHERE nguoi_ban=$1", user_id)

        uid_str = str(user_id)
        rows = await conn.fetch("SELECT boss_id, nguoi_tan_cong FROM boss_state")
        for row in rows:
            boss_id, ntc_raw = row["boss_id"], row["nguoi_tan_cong"]
            try:
                ntc = json.loads(ntc_raw or "{}")
                changed = False
                if uid_str in ntc:
                    del ntc[uid_str]; changed = True
                if "_log" in ntc and isinstance(ntc["_log"], list):
                    new_log = [l for l in ntc["_log"] if str(user_id) not in str(l)]
                    if len(new_log) != len(ntc["_log"]):
                        ntc["_log"] = new_log; changed = True
                if ntc.get("_killer") in (user_id, uid_str):
                    del ntc["_killer"]; changed = True
                if changed:
                    await conn.execute(
                        "UPDATE boss_state SET nguoi_tan_cong=$1 WHERE boss_id=$2",
                        json.dumps(ntc, ensure_ascii=False), boss_id
                    )
            except Exception:
                log.exception("Lỗi database")


async def add_linh_thach(user_id: int, so: int):
    _enqueue(
        "UPDATE tu_si SET linh_thach=GREATEST(0,linh_thach+$2) WHERE user_id=$1",
        (int(user_id), int(so))
    )


async def get_bang_xep_hang(guild_id_list=None, top: int = 10) -> list:
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """SELECT user_id, dao_hieu, linh_can, canh_gioi, cap_nho, linh_thach, thang_pvp, thua_pvp
               FROM tu_si ORDER BY canh_gioi DESC, cap_nho DESC, exp DESC LIMIT $1""",
            top
        )
        return [dict(r) for r in rows]


async def get_bxh_tong_tu_vi(top: int = 10) -> list:
    """BXH theo tổng tu vi tích lũy."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """SELECT user_id, dao_hieu, tong_tu_vi, canh_gioi, cap_nho
               FROM tu_si WHERE tong_tu_vi > 0
               ORDER BY tong_tu_vi DESC LIMIT $1""",
            top
        )
        return [dict(r) for r in rows]


async def get_bxh_linh_thach(top: int = 10) -> list:
    """BXH theo linh thạch hiện có."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """SELECT user_id, dao_hieu, linh_thach, canh_gioi, cap_nho
               FROM tu_si WHERE linh_thach > 0
               ORDER BY linh_thach DESC LIMIT $1""",
            top
        )
        return [dict(r) for r in rows]


async def get_bxh_linh_can(top: int = 10) -> list:
    """BXH theo tổng số linh căn sở hữu (lớp 1 + lớp 2)."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        # Lấy rộng để tính toán phía Python (JSON array length không dễ sort trong SQLite)
        rows = await conn.fetch(
            """SELECT user_id, dao_hieu, linh_can_so_huu, linh_can_lop2, canh_gioi, cap_nho
               FROM tu_si""",
        )
        import json as _json
        results = []
        for r in rows:
            d = dict(r)
            try:
                lc1 = _json.loads(d.get("linh_can_so_huu") or "[]")
                # linh_can_lop2 là dict stat buffs (hoi_tam, ho_tam...), không phải list linh căn
                # → chỉ đếm linh_can_so_huu
                total = len(lc1)
            except Exception:
                total = 0
            if total == 0:
                continue
            d["tong_linh_can"] = total
            results.append(d)
        results.sort(key=lambda x: x["tong_linh_can"], reverse=True)
        return results[:top]


async def get_bxh_chien_luc(top: int = 10) -> list:
    """BXH theo chiến lực = at*10 + df*8 + hp_e*0.1 — tính phía Python từ stats."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """SELECT user_id, dao_hieu, canh_gioi, cap_nho,
                      cong, thu, hp_max
               FROM tu_si WHERE canh_gioi >= 0""",
        )
    results = []
    for r in rows:
        d = dict(r)
        at  = d.get("cong", 0)
        df  = d.get("thu", 0)
        hp  = d.get("hp_max", 0)
        cl  = int(at * 10 + df * 8 + hp * 0.1)
        if cl <= 0:
            continue
        d["chien_luc"] = cl
        results.append(d)
    results.sort(key=lambda x: x["chien_luc"], reverse=True)
    return results[:top]


# ══════════════════════════════════════════════════════
#  RE-EXPORTS — split modules
# ══════════════════════════════════════════════════════
from utils.db_boss import *
from utils.db_market import *
from utils.db_social import *
