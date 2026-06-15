from __future__ import annotations
import logging
import json
import time
from typing import Any
from utils.database import get_pool, _enqueue

log = logging.getLogger("database")


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


async def get_phien_cho_item(phien_id: int) -> dict | None:
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
    item_loai: loại item ('Linh Quả' | 'Mảnh Linh Căn' | 'Đan Dược' | ...) — dùng khi rollback trùng sinh
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
