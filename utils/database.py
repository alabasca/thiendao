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
import datetime as _dt
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
_worker_task: "asyncio.Task | None" = None


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
    van_dinh_all_stat_pct REAL  DEFAULT 0
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
    """Tính thể lực chính hiện tại (hồi 1 phút/điểm, tối đa 250+CG×20)."""
    import time as _time
    cg = ts.get("canh_gioi", 0)
    tl_max = the_luc_toi_da(cg)
    tl = ts.get("the_luc", tl_max)
    cap_nhat = ts.get("the_luc_cap_nhat", 0)
    if tl >= tl_max:
        return tl_max
    elapsed = int(_time.time()) - cap_nhat
    hoi = elapsed // THE_LUC_HOI
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
async def get_tu_si(user_id: int) -> "dict | None":
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
#  WORLD CHAT
# ══════════════════════════════════════════════════════

async def get_world_chat_channels() -> list:
    """Lấy tất cả channel đăng ký world chat (kể cả inactive)."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            "SELECT guild_id, channel_id, webhook_url, active, thread_id FROM world_chat_channels ORDER BY created_at"
        )
        return [dict(r) for r in rows]


async def get_world_chat_by_guild(guild_id: int) -> "dict | None":
    """Lấy config world chat của 1 guild."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT guild_id, channel_id, webhook_url, active, thread_id FROM world_chat_channels WHERE guild_id=$1",
            guild_id
        )
        return dict(row) if row else None


async def set_world_chat_channel(guild_id: int, channel_id: int, webhook_url: str, thread_id: "int | None" = None):
    """Đăng ký hoặc cập nhật world chat channel cho guild."""
    import time as _time
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute("""
            INSERT INTO world_chat_channels (guild_id, channel_id, webhook_url, active, created_at, thread_id)
            VALUES ($1, $2, $3, 1, $4, $5)
            ON CONFLICT (guild_id) DO UPDATE SET
                channel_id  = EXCLUDED.channel_id,
                webhook_url = EXCLUDED.webhook_url,
                active      = 1,
                created_at  = EXCLUDED.created_at,
                thread_id   = EXCLUDED.thread_id
        """, guild_id, channel_id, webhook_url, int(_time.time()), thread_id)


async def disable_world_chat(guild_id: int):
    """Tắt world chat cho guild (giữ record để có thể bật lại)."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            "UPDATE world_chat_channels SET active=0 WHERE guild_id=$1",
            guild_id
        )


async def mark_webhook_inactive(guild_id: int):
    """Đánh dấu webhook dead (404/401) — tự động khi forward thất bại."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            "UPDATE world_chat_channels SET active=0 WHERE guild_id=$1",
            guild_id
        )


# ══════════════════════════════════════════════════════
#  CROSS PvP CHALLENGES
# ══════════════════════════════════════════════════════
async def create_cross_challenge(
    challenger_id: int, challenger_guild: int, target_id: int, cuoc_lt: int
) -> int:
    """Tạo lời thách đấu liên server. Trả về challenge ID."""
    now = int(time.time())
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """INSERT INTO cross_pvp_challenges
               (challenger_id, challenger_guild, target_id, cuoc_lt, created_at, status)
               VALUES ($1, $2, $3, $4, $5, 'pending')
               RETURNING id""",
            challenger_id, challenger_guild, target_id, cuoc_lt, now,
        )
        return row["id"]


async def get_cross_challenge(challenge_id: int) -> "dict | None":
    """Lấy thông tin 1 challenge theo ID."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT * FROM cross_pvp_challenges WHERE id=$1", challenge_id
        )
        return dict(row) if row else None


async def get_pending_cross_challenge(target_id: int) -> "dict | None":
    """Lấy lời thách đấu pending đầu tiên dành cho target_id."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """SELECT * FROM cross_pvp_challenges
               WHERE target_id=$1 AND status='pending'
               ORDER BY created_at ASC LIMIT 1""",
            target_id,
        )
        return dict(row) if row else None


async def get_pending_by_challenger(challenger_id: int) -> "dict | None":
    """Kiểm tra challenger đang có thách đấu pending không."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """SELECT * FROM cross_pvp_challenges
               WHERE challenger_id=$1 AND status='pending'
               ORDER BY created_at DESC LIMIT 1""",
            challenger_id,
        )
        return dict(row) if row else None


async def resolve_cross_challenge(challenge_id: int, status: str):
    """Đổi status challenge: 'accepted' | 'declined' | 'expired'."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            "UPDATE cross_pvp_challenges SET status=$1 WHERE id=$2",
            status, challenge_id,
        )


# ══════════════════════════════════════════════════════════════
#  ACTIVE VOTE
# ══════════════════════════════════════════════════════════════

async def save_active_vote(question: str, start_ts: int, end_ts: int,
                           votes: dict, messages: dict) -> None:
    """Upsert trạng thái vote đang mở vào DB."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute("""
            INSERT INTO active_vote (id, question, start_ts, end_ts, votes_json, msgs_json)
            VALUES (1, $1, $2, $3, $4, $5)
            ON CONFLICT (id) DO UPDATE SET
                question   = EXCLUDED.question,
                start_ts   = EXCLUDED.start_ts,
                end_ts     = EXCLUDED.end_ts,
                votes_json = EXCLUDED.votes_json,
                msgs_json  = EXCLUDED.msgs_json
        """, question, start_ts, end_ts,
             json.dumps(votes, ensure_ascii=False),
             json.dumps(messages, ensure_ascii=False))


async def update_active_vote_data(votes: dict, messages: dict) -> None:
    """Cập nhật phiếu bầu và danh sách message vào DB."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute("""
            UPDATE active_vote SET votes_json=$1, msgs_json=$2 WHERE id=1
        """, json.dumps(votes, ensure_ascii=False),
             json.dumps(messages, ensure_ascii=False))


async def load_active_vote() -> "dict | None":
    """Lấy vote đang mở từ DB. Trả về None nếu không có."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow("SELECT * FROM active_vote WHERE id=1")
        if not row:
            return None
        return {
            "question":   row["question"],
            "start_ts":   row["start_ts"],
            "end_ts":     row["end_ts"],
            "votes":      json.loads(row["votes_json"] or "{}"),
            "messages":   json.loads(row["msgs_json"]  or "{}"),
        }


async def clear_active_vote() -> None:
    """Xóa vote khỏi DB sau khi đã đóng."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute("DELETE FROM active_vote WHERE id=1")


async def expire_old_cross_challenges():
    """Đánh dấu expired các challenge quá 5 phút."""
    cutoff = int(time.time()) - 300
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            """UPDATE cross_pvp_challenges
               SET status='expired'
               WHERE status='pending' AND created_at < $1""",
            cutoff,
        )


async def dang_ban(user_id: int, loai: str, item_id, so_luong: int, gia: int, item_key: str = "") -> int:
    if isinstance(item_id, str):
        item_key = item_id; item_id = 0
    now = int(time.time())
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """INSERT INTO phien_cho (nguoi_ban, loai, item_id, item_key, so_luong, gia, thoi_gian)
               VALUES ($1,$2,$3,$4,$5,$6,$7) RETURNING id""",
            user_id, loai, item_id, item_key, so_luong, gia, now
        )
        return row["id"]


async def get_phien_cho(da_ban: bool = False) -> list:
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            "SELECT * FROM phien_cho WHERE da_ban=$1 ORDER BY thoi_gian DESC LIMIT 200",
            1 if da_ban else 0
        )
        return [dict(r) for r in rows]


async def get_phien_cho_item(phien_id: int) -> "dict | None":
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow("SELECT * FROM phien_cho WHERE id=$1", phien_id)
        return dict(row) if row else None


async def mua_phien_cho(phien_id: int) -> bool:
    pool = await get_pool()
    async with pool.acquire() as conn:
        result = await conn.execute(
            "UPDATE phien_cho SET da_ban=1 WHERE id=$1 AND da_ban=0", phien_id
        )
        return result.split()[-1] != "0"


async def cancel_phien_cho(phien_id: int, user_id: int) -> bool:
    pool = await get_pool()
    async with pool.acquire() as conn:
        result = await conn.execute(
            "UPDATE phien_cho SET da_ban=1 WHERE id=$1 AND nguoi_ban=$2 AND da_ban=0",
            phien_id, user_id
        )
        return result.split()[-1] != "0"


async def get_expired_phien_cho(expire_secs: int = 172800) -> list:
    """Lấy danh sách phiên chợ đã quá hạn (mặc định 2 ngày = 172800s) chưa bán và chưa bị cancel.
    Trả về list dict mỗi phiên: id, nguoi_ban, loai, item_id, item_key, so_luong, gia, thoi_gian.
    """
    pool  = await get_pool()
    cutoff = int(time.time()) - expire_secs
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            "SELECT * FROM phien_cho WHERE da_ban=0 AND thoi_gian < $1 ORDER BY thoi_gian ASC",
            cutoff
        )
        return [dict(r) for r in rows]


# ══════════════════════════════════════════════════════
#  BOSS STATE
# ══════════════════════════════════════════════════════
async def get_boss_state(boss_id: int) -> "dict | None":
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow("SELECT * FROM boss_state WHERE boss_id=$1", boss_id)
        if row:
            d = dict(row)
            d["nguoi_tan_cong"] = json.loads(d["nguoi_tan_cong"] or "{}")
            return d
    return None


async def upsert_boss(boss_id: int, hp_hien: int, spawn_time: int, nguoi_tan_cong: dict,
                      canh_gioi: int = 3, message_id: int = 0, channel_id: int = 0):
    ntc_json = json.dumps(nguoi_tan_cong, ensure_ascii=False)
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute("""
            INSERT INTO boss_state (boss_id, hp_hien, spawn_time, nguoi_tan_cong, canh_gioi, message_id, channel_id)
            VALUES ($1,$2,$3,$4,$5,$6,$7)
            ON CONFLICT (boss_id) DO UPDATE SET
                hp_hien         = EXCLUDED.hp_hien,
                nguoi_tan_cong  = EXCLUDED.nguoi_tan_cong,
                message_id      = CASE WHEN EXCLUDED.message_id != 0 THEN EXCLUDED.message_id ELSE boss_state.message_id END,
                channel_id      = CASE WHEN EXCLUDED.channel_id != 0 THEN EXCLUDED.channel_id ELSE boss_state.channel_id END
        """, boss_id, hp_hien, spawn_time, ntc_json, canh_gioi, message_id, channel_id)


async def spawn_boss(boss_id: int, hp_hien: int, spawn_time: int, nguoi_tan_cong: dict,
                     canh_gioi: int = 3, message_id: int = 0, channel_id: int = 0):
    ntc_json = json.dumps(nguoi_tan_cong, ensure_ascii=False)
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute("""
            INSERT INTO boss_state (boss_id, hp_hien, spawn_time, nguoi_tan_cong, canh_gioi, message_id, channel_id)
            VALUES ($1,$2,$3,$4,$5,$6,$7)
            ON CONFLICT (boss_id) DO UPDATE SET
                hp_hien        = EXCLUDED.hp_hien,
                spawn_time     = EXCLUDED.spawn_time,
                nguoi_tan_cong = EXCLUDED.nguoi_tan_cong,
                canh_gioi      = EXCLUDED.canh_gioi,
                message_id     = EXCLUDED.message_id,
                channel_id     = EXCLUDED.channel_id
        """, boss_id, hp_hien, spawn_time, ntc_json, canh_gioi, message_id, channel_id)


async def save_boss_guild_message(boss_id: int, guild_id: int, msg_id: int, channel_id: int):
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute("""
            INSERT INTO boss_guild_messages (boss_id, guild_id, msg_id, channel_id)
            VALUES ($1,$2,$3,$4)
            ON CONFLICT (boss_id, guild_id) DO UPDATE SET
                msg_id     = EXCLUDED.msg_id,
                channel_id = EXCLUDED.channel_id
        """, boss_id, guild_id, msg_id, channel_id)


async def get_boss_guild_messages(boss_id: int) -> list:
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            "SELECT guild_id, msg_id, channel_id FROM boss_guild_messages WHERE boss_id=$1", boss_id
        )
        return [(r["guild_id"], r["msg_id"], r["channel_id"]) for r in rows]


async def clear_boss_guild_messages(boss_id: int):
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute("DELETE FROM boss_guild_messages WHERE boss_id=$1", boss_id)


async def save_boss_message_id(boss_id: int, message_id: int, channel_id: int):
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            "UPDATE boss_state SET message_id=$1, channel_id=$2 WHERE boss_id=$3",
            message_id, channel_id, boss_id
        )


async def set_boss_end_time(boss_id: int, end_time: int):
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            "UPDATE boss_state SET end_time=$1 WHERE boss_id=$2", end_time, boss_id
        )
        # Lưu spawn_time đã kết thúc vào boss_ended_spawns để tra cứu sau khi boss_state bị reset
        row = await conn.fetchrow("SELECT spawn_time FROM boss_state WHERE boss_id=$1", boss_id)
        if row and row["spawn_time"] and row["spawn_time"] > 0:
            await conn.execute("""
                INSERT INTO boss_ended_spawns (boss_id, spawn_time, end_time)
                VALUES ($1, $2, $3)
                ON CONFLICT (boss_id, spawn_time) DO UPDATE SET end_time = EXCLUDED.end_time
            """, boss_id, row["spawn_time"], end_time)


async def set_boss_killer_atomic(boss_id: int, killer_uid: int, total_dmg: int,
                                  spawn_time: int, log_entry: str) -> bool:
    """Cập nhật HP boss, set _killer, và thêm log entry — atomic với row-level lock.

    Trả về True nếu đây là người đánh hạ boss (hp sau <= 0),
    False nếu boss đã chết trước (bởi người khác) hoặc vẫn còn sống.

    Dùng FOR UPDATE để tránh race condition: chỉ 1 request thắng cuộc đua set _killer.
    """
    import json as _j
    pool = await get_pool()
    async with pool.acquire() as conn:
        async with conn.transaction():
            row = await conn.fetchrow(
                "SELECT hp_hien, nguoi_tan_cong, spawn_time FROM boss_state WHERE boss_id=$1 FOR UPDATE",
                boss_id
            )
            if not row:
                return False

            hp_hien   = row["hp_hien"]
            spawn_db  = row["spawn_time"]
            ntc       = _j.loads(row["nguoi_tan_cong"] or "{}")

            # Nếu spawn_time không khớp → spawn đã reset (boss đã chết, spawn mới)
            if spawn_db != spawn_time:
                return False

            uid_str = str(killer_uid)
            ntc[uid_str] = ntc.get(uid_str, 0) + total_dmg

            hp_new   = max(0, hp_hien - total_dmg)
            is_kill  = hp_new <= 0

            if is_kill and "_killer" not in ntc:
                ntc["_killer"] = killer_uid

            # Cập nhật log (5 entries cuối)
            prev_log = ntc.get("_log", [])
            if not isinstance(prev_log, list):
                prev_log = []
            ntc["_log"] = (prev_log + [log_entry])[-5:]

            await conn.execute(
                "UPDATE boss_state SET hp_hien=$1, nguoi_tan_cong=$2 WHERE boss_id=$3",
                hp_new, _j.dumps(ntc, ensure_ascii=False), boss_id
            )

    return is_kill


async def get_boss_message_id(boss_id: int) -> "tuple[int, int]":
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT message_id, channel_id FROM boss_state WHERE boss_id=$1", boss_id
        )
        return (row["message_id"] or 0, row["channel_id"] or 0) if row else (0, 0)


async def add_boss_damage(boss_id: int, user_id: int, damage: int, spawn_time: int = 0):
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute("""
            INSERT INTO boss_tham_gia (boss_id, user_id, spawn_time, tong_damage)
            VALUES ($1,$2,$3,$4)
            ON CONFLICT (boss_id, user_id, spawn_time) DO UPDATE SET
                tong_damage = boss_tham_gia.tong_damage + $4
        """, boss_id, user_id, spawn_time, damage)


async def has_nhan_thuong(boss_id: int, user_id: int, spawn_time: int = 0) -> bool:
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT da_nhan FROM boss_tham_gia WHERE boss_id=$1 AND user_id=$2 AND spawn_time=$3",
            boss_id, user_id, spawn_time
        )
        return bool(row and row["da_nhan"])


async def mark_nhan_thuong(boss_id: int, user_id: int, spawn_time: int = 0):
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            "UPDATE boss_tham_gia SET da_nhan=1 WHERE boss_id=$1 AND user_id=$2 AND spawn_time=$3",
            boss_id, user_id, spawn_time
        )


async def get_boss_leaderboard(boss_id: int, spawn_time: int = 0) -> list:
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch("""
            SELECT user_id, SUM(tong_damage) as tong_damage
            FROM boss_tham_gia
            WHERE boss_id=$1 AND spawn_time=$2
            GROUP BY user_id
            ORDER BY tong_damage DESC
        """, boss_id, spawn_time)
        return [dict(r) for r in rows]


# ══════════════════════════════════════════════════════
#  QUAN HỆ
# ══════════════════════════════════════════════════════
def _qh_key(a: int, b: int) -> "tuple[int, int]":
    return (min(a, b), max(a, b))


async def get_quan_he(user_a: int, user_b: int) -> "dict | None":
    pool = await get_pool()
    a, b = _qh_key(user_a, user_b)
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT * FROM quan_he WHERE user_a=$1 AND user_b=$2", a, b
        )
        return dict(row) if row else None


async def upsert_quan_he(user_a: int, user_b: int, diem_delta: int = 0, loai: str = None):
    a, b = _qh_key(user_a, user_b)
    now = int(time.time())
    pool = await get_pool()
    async with pool.acquire() as conn:
        existing = await conn.fetchrow(
            "SELECT * FROM quan_he WHERE user_a=$1 AND user_b=$2", a, b
        )
        if not existing:
            await conn.execute(
                "INSERT INTO quan_he (user_a, user_b, diem, loai, ngay_tao) VALUES ($1,$2,$3,$4,$5)",
                a, b, diem_delta, loai or "", now
            )
        else:
            new_diem = existing["diem"] + diem_delta
            new_loai = loai if loai is not None else existing["loai"]
            await conn.execute(
                "UPDATE quan_he SET diem=$1, loai=$2 WHERE user_a=$3 AND user_b=$4",
                new_diem, new_loai, a, b
            )
    return await get_quan_he(a, b)


async def set_quan_he_loai(user_a: int, user_b: int, loai: str):
    a, b = _qh_key(user_a, user_b)
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            "UPDATE quan_he SET loai=$1 WHERE user_a=$2 AND user_b=$3", loai, a, b
        )


async def get_danh_sach_quan_he(user_id: int) -> list:
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            "SELECT * FROM quan_he WHERE user_a=$1 OR user_b=$1 ORDER BY diem DESC", user_id
        )
        return [dict(r) for r in rows]


# ══════════════════════════════════════════════════════
#  TẶNG QUÀ LOG
# ══════════════════════════════════════════════════════
def _today_str() -> str:
    return _dt.date.today().isoformat()


async def get_tang_qua_hom_nay(user_id: int, target_id: int) -> int:
    pool = await get_pool()
    ngay = _today_str()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT diem_tang FROM tang_qua_log WHERE user_id=$1 AND target_id=$2 AND ngay=$3",
            user_id, target_id, ngay
        )
        return row["diem_tang"] if row else 0


async def add_tang_qua_log(user_id: int, target_id: int, diem: int):
    ngay = _today_str()
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute("""
            INSERT INTO tang_qua_log (user_id, target_id, ngay, diem_tang)
            VALUES ($1,$2,$3,$4)
            ON CONFLICT (user_id, target_id, ngay) DO UPDATE SET
                diem_tang = tang_qua_log.diem_tang + $4
        """, user_id, target_id, ngay, diem)


# ══════════════════════════════════════════════════════
#  GUILD CONFIG
# ══════════════════════════════════════════════════════
async def get_boss_channel(guild_id: int) -> int:
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT boss_channel_id FROM guild_config WHERE guild_id=$1", guild_id
        )
        return row["boss_channel_id"] if row else 0


async def set_boss_channel(guild_id: int, channel_id: int):
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute("""
            INSERT INTO guild_config (guild_id, boss_channel_id)
            VALUES ($1,$2)
            ON CONFLICT (guild_id) DO UPDATE SET boss_channel_id = EXCLUDED.boss_channel_id
        """, guild_id, channel_id)


# ══════════════════════════════════════════════════════
#  BOSS DATA CLEANUP
# ══════════════════════════════════════════════════════



async def is_boss_spawn_ended(boss_id: int, spawn_time: int) -> bool:
    """Kiểm tra spawn_time này đã kết thúc chưa (dùng boss_ended_spawns, không phụ thuộc boss_state)."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT end_time FROM boss_ended_spawns WHERE boss_id=$1 AND spawn_time=$2",
            boss_id, spawn_time)
        return bool(row)

async def get_unclaimed_boss_spawns(user_id: int) -> list:
    """Trả về list các (boss_id, spawn_time, tong_damage) mà user đã tham gia nhưng chưa nhận thưởng.
    Query trực tiếp boss_tham_gia — không phụ thuộc vào boss_state.spawn_time (có thể đã bị reset).
    """
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch("""
            SELECT boss_id, spawn_time, tong_damage
            FROM boss_tham_gia
            WHERE user_id=$1 AND da_nhan=0 AND spawn_time > 0
            ORDER BY spawn_time DESC
        """, user_id)
        return [dict(r) for r in rows]

async def cleanup_old_boss_data(days: int = 2):
    """Xóa boss_tham_gia của các lần spawn cũ hơn N ngày — chạy định kỳ."""
    import time as _t
    cutoff = int(_t.time()) - days * 86400
    pool = await get_pool()
    async with pool.acquire() as conn:
        result = await conn.execute(
            "DELETE FROM boss_tham_gia WHERE spawn_time < $1", cutoff)
    log.info(f"[BossClean] Đã xóa boss_tham_gia cũ hơn {days} ngày (cutoff={cutoff})")


async def clear_boss_data(boss_id: int, purge_rewards: bool = True):
    """Reset boss state để spawn mới.
    purge_rewards=True (default): XÓA boss_tham_gia — reset hoàn toàn mỗi spawn.
    purge_rewards=False: GIỮ boss_tham_gia (legacy path — không dùng nữa).
    """
    pool = await get_pool()
    async with pool.acquire() as conn:
        if purge_rewards:
            await conn.execute("DELETE FROM boss_tham_gia WHERE boss_id=$1", boss_id)
        await conn.execute(
            "UPDATE boss_state SET nguoi_tan_cong='{}', message_id=0, channel_id=0, hp_hien=0, spawn_time=0 WHERE boss_id=$1",
            boss_id
        )
    log.info(f"[BossClean] Reset boss_id={boss_id} (purge_rewards={purge_rewards})")


# ══════════════════════════════════════════════════════
#  RESET LOG
# ══════════════════════════════════════════════════════
async def _ensure_reset_log(conn) -> None:
    """Tạo bảng reset_log nếu chưa tồn tại."""
    await conn.execute("""
        CREATE TABLE IF NOT EXISTS reset_log (
            user_id      BIGINT  PRIMARY KEY,
            so_lan_reset INTEGER DEFAULT 0
        );
    """)


async def get_reset_count(user_id: int) -> int:
    pool = await get_pool()
    async with pool.acquire() as conn:
        await _ensure_reset_log(conn)
        row = await conn.fetchrow(
            "SELECT so_lan_reset FROM reset_log WHERE user_id=$1", user_id)
    return row["so_lan_reset"] if row else 0


async def increment_reset_count(user_id: int) -> int:
    pool = await get_pool()
    async with pool.acquire() as conn:
        await _ensure_reset_log(conn)
        row = await conn.fetchrow("""
            INSERT INTO reset_log (user_id, so_lan_reset)
            VALUES ($1, 1)
            ON CONFLICT (user_id) DO UPDATE
              SET so_lan_reset = reset_log.so_lan_reset + 1
            RETURNING so_lan_reset
        """, user_id)
    return row["so_lan_reset"] if row else 1


async def buy_phap_bao_atomic(user_id: int, pb_id: int, gia: int, pb_list_after: list) -> bool:
    """Mua pháp bảo atomic: trừ LT và thêm pb_id chỉ khi LT đủ VÀ chưa sở hữu.
    Trả về True nếu thành công, False nếu không đủ LT hoặc đã sở hữu."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        async with conn.transaction():
            row = await conn.fetchrow(
                "SELECT linh_thach, phap_bao FROM tu_si WHERE user_id=$1 FOR UPDATE",
                user_id)
            if not row:
                return False
            pb_raw = row["phap_bao"]
            pb_owned = json.loads(pb_raw) if isinstance(pb_raw, str) else (pb_raw or [])
            if pb_id in pb_owned:
                return False  # đã sở hữu
            if row["linh_thach"] < gia:
                return False  # không đủ LT
            new_pb = json.dumps(pb_list_after)
            await conn.execute(
                "UPDATE tu_si SET linh_thach=linh_thach-$1, phap_bao=$2 WHERE user_id=$3",
                gia, new_pb, user_id)
    return True


async def claim_first_hit_reward(boss_id: int, user_id: int, spawn_time: int,
                                  lt: int, exp: int) -> bool:
    """Trao thưởng first-hit atomic — chỉ thành công 1 lần duy nhất per user/boss/spawn.
    Dùng INSERT ON CONFLICT DO NOTHING: nếu row đã có → trả False (đã nhận rồi).
    Trả về True nếu vừa insert (= first hit thực sự), False nếu đã tồn tại."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        async with conn.transaction():
            result = await conn.execute("""
                INSERT INTO boss_tham_gia (boss_id, user_id, spawn_time, tong_damage, da_nhan)
                VALUES ($1,$2,$3,0,1)
                ON CONFLICT (boss_id, user_id, spawn_time) DO NOTHING
            """, boss_id, user_id, spawn_time)
            # rowcount=1 nghĩa là vừa INSERT thành công = first hit
            inserted = result == "INSERT 0 1"
            if inserted:
                await conn.execute(
                    "UPDATE tu_si SET linh_thach=linh_thach+$1, exp=exp+$2 WHERE user_id=$3",
                    lt, exp, user_id)
    return inserted


async def transfer_dan_duoc_atomic(sender_id: int, target_id: int,
                                    dan_key: str, so_luong: int) -> bool:
    """Chuyển đan dược atomic từ sender → target.
    Trả về True nếu thành công, False nếu sender không đủ số lượng."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        async with conn.transaction():
            # Lock sender row trước
            row_s = await conn.fetchrow(
                "SELECT dan_duoc FROM tu_si WHERE user_id=$1 FOR UPDATE", sender_id)
            if not row_s:
                return False
            kho_s = json.loads(row_s["dan_duoc"]) if isinstance(row_s["dan_duoc"], str) else (row_s["dan_duoc"] or {})
            co = kho_s.get(dan_key, 0)
            if co < so_luong:
                return False
            kho_s[dan_key] = co - so_luong
            if kho_s[dan_key] <= 0:
                del kho_s[dan_key]
            await conn.execute(
                "UPDATE tu_si SET dan_duoc=$1 WHERE user_id=$2",
                json.dumps(kho_s), sender_id)
            # Lock target row
            row_t = await conn.fetchrow(
                "SELECT dan_duoc FROM tu_si WHERE user_id=$1 FOR UPDATE", target_id)
            if not row_t:
                return False
            kho_t = json.loads(row_t["dan_duoc"]) if isinstance(row_t["dan_duoc"], str) else (row_t["dan_duoc"] or {})
            kho_t[dan_key] = kho_t.get(dan_key, 0) + so_luong
            await conn.execute(
                "UPDATE tu_si SET dan_duoc=$1 WHERE user_id=$2",
                json.dumps(kho_t), target_id)
    return True


async def log_giao_dich(loai: str, sender_id: int, receiver_id: int,
                         item_name: str = "", so_luong: int = 1,
                         gia_lt: int = 0, ghi_chu: str = "",
                         item_loai: str = "", item_key: str = "") -> None:
    """Ghi log giao dịch giữa người chơi.
    loai: 'phien_cho' | 'tang_lt' | 'tang_dan' | 'private_trade'
    item_loai: loại item ('Linh Quả' | 'Mảnh Linh Căn' | ...) — dùng khi rollback trùng sinh
    item_key: key của item (lq_id, nl_id, ...) — dùng khi rollback trùng sinh
    """
    _enqueue("""
        INSERT INTO giao_dich_log
            (loai, sender_id, receiver_id, item_name, item_loai, item_key,
             so_luong, gia_lt, thoi_gian, ghi_chu)
        VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10)
    """, (loai, sender_id, receiver_id, item_name, item_loai, item_key,
          so_luong, gia_lt, int(time.time()), ghi_chu))


async def get_giao_dich_log(user_id: int | None = None, loai: str | None = None,
                             limit: int = 50, offset: int = 0) -> list[dict[str, Any]]:
    """Lấy log giao dịch. Lọc theo user_id (sender hoặc receiver) và/hoặc loại."""
    pool = await get_pool()
    # Build query an toàn — user_id dùng 2 lần nên thêm vào params 2 lần
    conditions = []
    params = []
    if user_id:
        i1 = len(params) + 1
        i2 = len(params) + 2
        conditions.append(f"(sender_id=${i1} OR receiver_id=${i2})")
        params.append(user_id)
        params.append(user_id)
    if loai:
        i = len(params) + 1
        conditions.append(f"loai=${i}")
        params.append(loai)
    where = ("WHERE " + " AND ".join(conditions)) if conditions else ""
    i_limit  = len(params) + 1
    i_offset = len(params) + 2
    params += [limit, offset]
    async with pool.acquire() as conn:
        rows = await conn.fetch(f"""
            SELECT * FROM giao_dich_log
            {where}
            ORDER BY thoi_gian DESC
            LIMIT ${i_limit} OFFSET ${i_offset}
        """, *params)
    return [dict(r) for r in rows]


# ══════════════════════════════════════════════════════
#  TRÙNG SINH / VẤN ĐỈNH TIÊN TÔN
# ══════════════════════════════════════════════════════

async def thuc_hien_trung_sinh(user_id: int, bonus_all_stat_pct: float = 0.0) -> dict:
    """
    Thực hiện trùng sinh nhân vật.

    Giữ lại : dao_hieu, the_chat, sung_thu, sung_thu_active,
               linh_can_so_huu (điểm về 0), dotpha_tc_nl,
               so_lan_trung_sinh, ti_le_van_dinh, van_dinh_all_stat_pct
    Xóa sạch của acc này: linh_thach, phap_bao, dan_duoc, nguyen_lieu, linh_qua,
            manh_linh_can, linh_can_diem, cong_phap, phien_cho,
      giao_dich_log 36h.

    Rollback đúng số lượng đã nhận từ acc trùng sinh (private_trade, 36h):
      - Linh Quả      → trừ đúng so_luong × diem_per_qua khỏi linh_can_diem
      - Mảnh Linh Căn → trừ đúng so_luong khỏi manh_linh_can
                        nếu đã ghép thành căn → xóa căn, trả lại số mảnh trước khi ghép
    """
    import time as _time

    try:
        from utils.config import LINH_QUA_BY_ID as _LINH_QUA_BY_ID
    except Exception:
        _LINH_QUA_BY_ID = {}

    pool = await get_pool()
    async with pool.acquire() as conn:
        async with conn.transaction():
            ts = await conn.fetchrow(
                "SELECT * FROM tu_si WHERE user_id=$1 FOR UPDATE", user_id)
            if not ts:
                return {}
            ts = dict(ts)

            # ── Tăng số lần trùng sinh + tỉ lệ Vấn Đỉnh mới ───────────────
            so_lan_moi = ts.get("so_lan_trung_sinh", 0) + 1
            ti_le_moi  = round(0.01 + so_lan_moi * 0.015, 4)
            bonus_all_stat_pct = max(0.0, float(bonus_all_stat_pct or 0.0))
            vd_bonus_moi = round(float(ts.get("van_dinh_all_stat_pct", 0.0) or 0.0) + bonus_all_stat_pct, 4)

            # ── Giữ lại linh căn sở hữu, reset điểm về 0 ───────────────────
            lc_ids = ts.get("linh_can_so_huu", [])
            if isinstance(lc_ids, str):
                try:    lc_ids = json.loads(lc_ids) if lc_ids else []
                except: lc_ids = []
            lc_diem_reset = {lc_id: 0 for lc_id in set(lc_ids)}

            # ── Lấy giao dịch private_trade gửi đi trong 36h ────────────────
            now_ts = int(_time.time())
            cutoff = now_ts - 36 * 3600
            recent_trades = await conn.fetch(
                """SELECT receiver_id, item_loai, item_key, so_luong
                   FROM giao_dich_log
                   WHERE loai='private_trade' AND sender_id=$1 AND thoi_gian >= $2
                     AND receiver_id IS NOT NULL AND receiver_id != $1
                   ORDER BY thoi_gian ASC""",
                user_id, cutoff
            )

            # Gom theo receiver
            from collections import defaultdict
            recv_trades = defaultdict(list)
            for row in recent_trades:
                recv_trades[row["receiver_id"]].append({
                    "item_loai": row["item_loai"] or "",
                    "item_key":  row["item_key"]  or "",
                    "so_luong":  row["so_luong"]  or 0,
                })

            # ── Rollback từng receiver (sort để tránh deadlock) ──────────────
            for recv_id in sorted(recv_trades.keys()):
                recv_row = await conn.fetchrow(
                    "SELECT * FROM tu_si WHERE user_id=$1 FOR UPDATE", recv_id)
                if not recv_row:
                    continue

                def _pj(d, f):
                    raw = d.get(f, {})
                    if isinstance(raw, dict): return raw.copy()
                    try: return json.loads(raw) if raw else {}
                    except: return {}

                def _pl(d, f):
                    raw = d.get(f, [])
                    if isinstance(raw, list): return raw.copy()
                    try: return json.loads(raw) if raw else []
                    except: return []

                recv_ts     = dict(recv_row)
                manh        = _pj(recv_ts, "manh_linh_can")
                lc_diem_r   = _pj(recv_ts, "linh_can_diem")
                lc_so_huu_r = _pl(recv_ts, "linh_can_so_huu")
                changed     = False

                for trade in recv_trades[recv_id]:
                    loai     = trade["item_loai"]
                    key      = trade["item_key"]
                    so_luong = trade["so_luong"]
                    if not key or so_luong <= 0:
                        continue

                    if loai == "Linh Quả":
                        # Trừ đúng số điểm đã nhận
                        diem_per = _LINH_QUA_BY_ID.get(key, {}).get("diem", 3)
                        lc_diem_r[key] = max(0, lc_diem_r.get(key, 0) - so_luong * diem_per)
                        changed = True

                    elif loai == "Mảnh Linh Căn":
                        manh_hien   = manh.get(key, 0)
                        so_lan_ghep = lc_so_huu_r.count(key)

                        if so_lan_ghep == 0:
                            # Chưa ghép: trừ thẳng số mảnh đã nhận
                            new_manh = manh_hien - so_luong
                            if new_manh <= 0:
                                manh.pop(key, None)
                            else:
                                manh[key] = new_manh
                        else:
                            # Đã ghép: tính lại số mảnh trước khi nhận từ acc trùng sinh
                            tong_truoc = manh_hien + 100 * so_lan_ghep - so_luong
                            if tong_truoc < 0: tong_truoc = 0
                            lan_ghep_truoc     = tong_truoc // 100
                            manh_con_lai_truoc = tong_truoc % 100
                            # Xóa số lớp linh căn thừa (từ phía cuối)
                            lan_xoa = so_lan_ghep - lan_ghep_truoc
                            if lan_xoa > 0:
                                new_lc = list(lc_so_huu_r)
                                for _ in range(lan_xoa):
                                    try:
                                        i = len(new_lc) - 1 - new_lc[::-1].index(key)
                                        new_lc.pop(i)
                                    except ValueError:
                                        break
                                lc_so_huu_r = new_lc
                                if key not in lc_so_huu_r:
                                    lc_diem_r.pop(key, None)
                            # Trả lại số mảnh đúng trước khi nhận
                            if manh_con_lai_truoc > 0:
                                manh[key] = manh_con_lai_truoc
                            else:
                                manh.pop(key, None)
                        changed = True

                if changed:
                    await conn.execute(
                        """UPDATE tu_si SET
                               manh_linh_can=$1, linh_can_diem=$2, linh_can_so_huu=$3
                           WHERE user_id=$4""",
                        json.dumps(manh), json.dumps(lc_diem_r),
                        json.dumps(lc_so_huu_r), recv_id)

            # ── Xóa phiên chợ của acc này ────────────────────────────────────
            await conn.execute("DELETE FROM phien_cho WHERE nguoi_ban=$1", user_id)

            # ── Xóa giao dịch log 36h của acc này ───────────────────────────
            await conn.execute(
                """DELETE FROM giao_dich_log
                   WHERE (sender_id=$1 OR receiver_id=$1) AND thoi_gian >= $2""",
                user_id, cutoff)

            # ── Reset nhân vật về Luyện Khí Sơ Kỳ ───────────────────────────
            await conn.execute("""
                UPDATE tu_si SET
                    canh_gioi=0, cap_nho=1, exp=0,
                    hp=100, hp_max=100, cong=10, thu=5,
                    linh_thach=0,
                    phap_bao='[]', phap_bao_active=-1,
                    yeu_thu='[]', yeu_thu_active=-1,
                    dan_duoc='{}', nguyen_lieu='{}',
                    thang_pvp=0, thua_pvp=0,
                    cd_tu_luyen=0, cd_dot_pha=0, cd_khai_hoang=0,
                    cd_bi_canh=0, cd_diem_danh=0, chuoi_diem_danh=0,
                    tong_tu_luyen=0, danh_hieu_hien='',
                    the_luc=250, the_luc_cap_nhat=0,
                    tran_the_luc=0, tran_the_luc_cap_nhat=0,
                    cong_phap_so_huu='[]', cong_phap_trang_bi='{}',
                    cong_phap_tang='{}', cong_phap_hoc='[]', cong_phap_active=-1,
                    bc_thua_lan_truoc=0, tong_tu_vi=0,
                    linh_luc=0, hoi_tam=0, ho_tam=0, bao_kich=0, khang_bao=0,
                    linh_can_diem=$1, manh_linh_can='{}',
                    linh_qua='{}', linh_can_lop2='{}',
                    banner_id=0,
                    so_lan_trung_sinh=$2, ti_le_van_dinh=$3,
                    van_dinh_all_stat_pct=$4
                WHERE user_id=$5
            """, json.dumps(lc_diem_reset), so_lan_moi, ti_le_moi, vd_bonus_moi, user_id)

            ts_new = await conn.fetchrow("SELECT * FROM tu_si WHERE user_id=$1", user_id)
            return dict(ts_new) if ts_new else {}


async def get_giao_dich_log_recent(user_id: int, hours: int = 36) -> list:
    """Lấy các giao dịch gần đây (trong X giờ) liên quan đến user."""
    import time as _time
    cutoff = int(_time.time()) - hours * 3600
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """SELECT * FROM giao_dich_log
               WHERE (sender_id=$1 OR receiver_id=$1) AND thoi_gian >= $2
               ORDER BY thoi_gian DESC""",
            user_id, cutoff
        )
    return [dict(r) for r in rows]


# ══════════════════════════════════════════════════════
#  PROMO CODES (Shop)
# ══════════════════════════════════════════════════════

async def create_promo_code(code: str, goi: str, nguoi_tao: int) -> bool:
    """Tạo promo code mới. Trả về True nếu thành công."""
    pool = await get_pool()
    try:
        async with pool.acquire() as conn:
            await conn.execute(
                "INSERT INTO promo_codes (code, goi, nguoi_tao, ngay_tao) VALUES ($1,$2,$3,$4)",
                code, goi, nguoi_tao, int(time.time())
            )
        return True
    except Exception:
        return False


async def redeem_promo_code(code: str, user_id: int) -> "dict | None":
    """Đổi promo code. Trả về dict {code, goi} nếu thành công, None nếu code không hợp lệ/đã dùng."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT code, goi, nguoi_dung FROM promo_codes WHERE code=$1", code
        )
        if not row:
            return None
        if row["nguoi_dung"] and row["nguoi_dung"] != 0:
            return None  # đã dùng
        await conn.execute(
            "UPDATE promo_codes SET nguoi_dung=$1, ngay_dung=$2 WHERE code=$3",
            user_id, int(time.time()), code
        )
        return {"code": row["code"], "goi": row["goi"]}


async def get_promo_code_owner(code: str) -> int | None:
    """Lấy người tạo promo code."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT nguoi_tao FROM promo_codes WHERE code=$1", code
        )
        return row["nguoi_tao"] if row else None
