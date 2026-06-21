from __future__ import annotations
from typing import Any

from cogs.views._common import *
from utils.embeds import e_loi, e_ok, e_warn, e_info, safe_defer
import re as _re
import logging
from typing import TYPE_CHECKING
from cogs.views.private_trade import PrivateTradeModal, LOAI_BLOCK
from utils.bot_emojis import (
    E_SINH_LUC, E_LINH_LUC, E_CONG_KICH, E_PHONG_NGU,
    E_LINH_THACH, E_TT_LINH_THACH, E_HOI_TAM, E_HO_TAM, E_BAO_KICH, E_KHANG_BAO,
)
log = logging.getLogger("hoso")


async def _refresh_kho_after_modal(inter: discord.Interaction, kv: "KhoDoView",
                                    result_embed: discord.Embed, footer_text: str = ""):
    """Helper: gửi kết quả + refresh kho đồ sau modal submit.

    Strategy:
    - Modal inter không có inter.message → không dùng edit_message được
    - Dùng inter.edit_original_response() để update ephemeral message gốc (message chứa kho đồ)
    - Gửi result_embed qua followup riêng (ephemeral, tự dismiss sau vài giây)
    """
    from cogs.hoso_utils import _embed_kho_trang
    # Tạo view mới hoàn toàn để tránh interaction failed sau modal
    new_view = kv._new_view()
    kv.stop()
    kho_embed = _embed_kho_trang(new_view.ts, new_view.user, new_view.filtered_items, new_view.trang,
                                  tab_label=f"{new_view.TAB_EMOJIS[new_view.tab]} {new_view.tab}")
    if footer_text:
        kho_embed.set_footer(text=footer_text)

    # Bước 1: Gửi kết quả action (followup ephemeral)
    await safe_followup(inter, embed=result_embed, ephemeral=True)

    # Bước 2: Update kho đồ — thử edit_original_response trước (update đúng message đã mở kho)
    try:
        await inter.edit_original_response(embed=kho_embed, view=new_view)
        return
    except Exception:
        log.exception("Lỗi kho_do")

    # Bước 3: Fallback — edit message được lưu trong kv._original_msg
    msg = getattr(kv, "_original_msg", None)
    if msg:
        try:
            await msg.edit(embed=kho_embed, view=new_view)
            return
        except Exception:
            log.exception("Lỗi kho_do")

    # Bước 4: Last resort — gửi message kho mới (người chơi cần dismiss cái cũ)
    await safe_followup(inter, embed=kho_embed, view=new_view, ephemeral=True)


def _check_lop_moi(diem_cu: int, diem_moi: int) -> list:
    """Trả về list các lớp mới đạt được sau khi điểm tăng."""
    from utils.config import LINH_CAN_DIEM_YEU_CAU
    return [lop for lop, nguong in sorted(LINH_CAN_DIEM_YEU_CAU.items())
            if diem_cu < nguong <= diem_moi]

if TYPE_CHECKING:
    from cogs.hoso import HoSoView

class BanLaiModal(discord.ui.Modal, title="Bán Lại Cho Shop"):
    sl_input = discord.ui.TextInput(
        label="Số lượng muốn bán", placeholder="1", default="1",
        min_length=1, max_length=3)

    def __init__(self, kho_view: "KhoDoView", item: dict, msg=None):
        super().__init__()
        self.kho_view = kho_view
        self.item     = item
        self.msg      = msg  # message gốc để edit sau
        so_co = item.get("so_luong", 1)
        self.sl_input.placeholder = f"Tối đa: {so_co} viên"

    async def on_submit(self, inter: discord.Interaction):
        try:
            sl = max(1, int(self.sl_input.value))
        except (ValueError, TypeError):
            return await inter.response.send_message("❌ Số không hợp lệ!", ephemeral=True)
        ts  = await get_tu_si(inter.user.id)
        # Hỗ trợ cả Đan Tu Luyện (_dtl_key) và Đan Dược (_dd_id)
        if self.item.get("loai") == "Đan Dược":
            key = str(self.item["_dd_id"])
            gia = self.item.get("_dd_gia", 0)
        else:
            key = self.item["_dtl_key"]
            gia = self.item.get("_dtl_gia", 0)
        co  = ts["dan_duoc"].get(key, 0)
        if sl > co:
            return await inter.response.send_message(
                f"❌ Chỉ có **{co}** viên!", ephemeral=True)
        gia_nhan = int(gia * 0.6) * sl
        dd = ts["dan_duoc"].copy()
        dd[key] = co - sl
        if dd[key] <= 0: del dd[key]
        await update_tu_si(inter.user.id, dan_duoc=dd)
        await add_linh_thach(inter.user.id, gia_nhan)
        # Refresh kho view và edit trực tiếp embed đang hiện
        kv = self.kho_view
        kv.ts    = await get_tu_si(inter.user.id)
        kv.items = _build_inventory(kv.ts)
        kv.sel_idx = min(kv.sel_idx, max(0, len(kv.items) - 1))
        kv._rebuild()
        # Modal respond
        if not await safe_defer(inter, ephemeral=True):
            return
        kho_embed = _embed_kho_trang(kv.ts, kv.user, kv.items, kv.trang)
        kho_embed.set_footer(text=f"✅ Đã bán {self.item['ten']} ×{sl} — +{fmt(gia_nhan)} LT")
        # Edit message kho đồ gốc (được lưu khi mở modal)
        result_embed = discord.Embed(
            title="✅ Đã bán",
            description=f"Đã bán {self.item['ten']} ×{sl} — +{fmt(gia_nhan)} LT",
            color=0x57F287)
        await _refresh_kho_after_modal(inter, kv, result_embed,
                                        footer_text=f"✅ Đã bán {self.item['ten']} ×{sl} — +{fmt(gia_nhan)} LT")



class TreoBanDTLModal(discord.ui.Modal, title="Treo Bán Phường Thị"):
    sl_input = discord.ui.TextInput(
        label="Số lượng muốn treo bán", placeholder="1", default="1",
        min_length=1, max_length=3)
    gia_input = discord.ui.TextInput(
        label="Giá/viên — Thiên đạo không thể định giá LT",
        placeholder="Nhập giá bán...",
        min_length=1, max_length=12)

    def __init__(self, parent: "HoSoView", item: dict, gia_goi_y: int):
        super().__init__()
        self.parent    = parent
        self.item      = item
        so_co = item.get("so_luong", 1)
        self.sl_input.placeholder = f"Tối đa: {so_co} viên"
        # Auto-fill giá gợi ý
        self.gia_input.default = str(gia_goi_y) if gia_goi_y > 0 else ""

    async def on_submit(self, inter: discord.Interaction):
        try:
            gia = int(self.gia_input.value.replace(",","").replace(".",""))
            sl  = max(1, int(self.sl_input.value))
        except (ValueError, TypeError):
            return await inter.response.send_message("❌ Số không hợp lệ!", ephemeral=True)
        if gia < 1:
            return await inter.response.send_message("❌ Giá phải lớn hơn 0!", ephemeral=True)

        await inter.response.defer(ephemeral=True)
        ts  = await get_tu_si(inter.user.id)
        key = self.item["_dtl_key"]
        co  = ts["dan_duoc"].get(key, 0)
        if co < sl:
            return await safe_followup(inter, 
                f"❌ Chỉ có **{co}** viên, không đủ **{sl}**!", ephemeral=True)

        # Trừ đan khỏi túi
        dd = ts["dan_duoc"].copy()
        dd[key] = co - sl
        if dd[key] <= 0: del dd[key]
        await update_tu_si(inter.user.id, dan_duoc=dd)

        # Đăng lên phường thị (loai="dtl", iid=key)
        pid = await dang_ban(inter.user.id, "dtl", key, sl, gia)
        await safe_followup(inter, 
            embed=discord.Embed(
                title="🏪 Treo bán thành công!",
                description=(
                    f"{self.item['emoji']} **{self.item['ten']}** ×{sl}\n"
                    f"Giá: **{fmt(gia)}** {E_LINH_THACH}/viên\n"
                    f"Mã phiên: **#{pid}**\n"
                    f"*(Người chơi toàn server có thể mua)*"
                ),
                color=0x5865F2),
            ephemeral=True)


class HopThanhModal(discord.ui.Modal):

    def __init__(self, kho_view: "KhoDoView", item: dict):
        lc = LINH_CAN_BY_ID.get(item.get("_lq_id", ""))
        ten_can = lc["ten"] if lc else "Linh Căn"
        co = item.get("so_luong", 0)
        super().__init__(title=f"Hợp Thành — {ten_can}")
        self.xac_nhan = discord.ui.TextInput(
            label=f"Có {co}/100 mảnh — nhập 'xác nhận'",
            placeholder="xác nhận",
            min_length=1, max_length=10)
        self.add_item(self.xac_nhan)
        self.kho_view = kho_view
        self.item     = item

    async def on_submit(self, inter: discord.Interaction):
        if self.xac_nhan.value.strip().lower() not in ("xác nhận", "xac nhan"):
            return await inter.response.send_message("❌ Không hợp thành.", ephemeral=True)

        lq_id = self.item.get("_lq_id")
        ts    = await get_tu_si(inter.user.id)
        manh  = ts.get("manh_linh_can", {})
        co    = manh.get(lq_id, 0)

        if co < 100:
            return await inter.response.send_message(
                f"❌ Chỉ có **{co}/100** mảnh, chưa đủ để ghép!", ephemeral=True)

        ghep_duoc = co // 100
        con_lai   = co % 100

        # Trừ mảnh
        manh_new = manh.copy()
        if con_lai > 0:
            manh_new[lq_id] = con_lai
        else:
            manh_new.pop(lq_id, None)

        # Thêm linh căn — giới hạn 9 loại unique, mỗi loại chỉ 1 lần
        MAX_LINH_CAN = 9
        lc_so_huu = ts.get("linh_can_so_huu", []).copy()
        lc_diem   = ts.get("linh_can_diem", {}).copy()
        da_co_can_nay  = lq_id in lc_so_huu
        so_unique_hien = len(set(lc_so_huu))

        if da_co_can_nay:
            _lc_data = LINH_CAN_BY_ID.get(lq_id, {})
            return await inter.response.send_message(
                f"❌ Đã sở hữu **{_lc_data.get('ten', lq_id)}**! Mỗi loại linh căn chỉ ghép được 1 lần.",
                ephemeral=True)
        if so_unique_hien >= MAX_LINH_CAN:
            return await inter.response.send_message(
                f"❌ Đã đạt giới hạn **{MAX_LINH_CAN} loại linh căn**! Không thể ghép thêm căn mới.",
                ephemeral=True)

        lc_so_huu.append(lq_id)
        if lq_id not in lc_diem:
            lc_diem[lq_id] = 0

        await update_tu_si(inter.user.id,
            manh_linh_can=manh_new,
            linh_can_so_huu=lc_so_huu,
            linh_can_diem=lc_diem)

        lc  = LINH_CAN_BY_ID.get(lq_id, {})
        kv  = self.kho_view
        kv.ts    = await get_tu_si(inter.user.id)
        kv.items = _build_inventory(kv.ts)
        kv.sel_idx = min(kv.sel_idx, max(0, len(kv.items) - 1))
        kv._rebuild()

        # Số lần đã có căn này TRƯỚC khi ghép lần này
        so_lop_truoc = lc_so_huu.count(lq_id) - ghep_duoc
        la_cong_lop  = so_lop_truoc >= 1
        lop_hien_tai = so_lop_truoc + ghep_duoc

        embed_ok = discord.Embed(
            title="🌟 LINH CĂN CỘNG LỚP!" if la_cong_lop else "✨ GHÉP LINH CĂN THÀNH CÔNG!",
            description=(
                f"{lc.get('emoji','')} **{lc.get('ten', lq_id)}** ×{ghep_duoc} đã được giác tỉnh!\n"
                + (f"Mảnh còn lại: **{con_lai}/100**\n" if con_lai > 0 else "")
                + (f"⚡ **Lớp {lop_hien_tai}** — Passive nhân ×{lop_hien_tai}!\n" if la_cong_lop else "")
                + f"\n*{lc.get('chuc_mung','')}*"
            ),
            color=0xFFD700 if la_cong_lop else lc.get("mau", 0x57F287))
        p = lc.get("passive", {})
        if p:
            _PLABEL = {"at_flat":"Tấn Công","df_flat":"Phòng Ngự","hp_flat":"Sinh Lực",
                       "hoi_tam":"Hội Tâm","ho_tam":"Hộ Tâm","bao_kich":"Bạo Kích",
                       "khang_bao":"Kháng Bạo","drop_rate":"Drop%","exp_pct":"Tu Vi+"}
            parts = []
            for k, v in p.items():
                lbl = _PLABEL.get(k, k)
                unit = "%" if k not in ("at_flat","df_flat","hp_flat","hoi_tam","ho_tam") else ""
                parts.append(f"{lbl} +{v}{unit}")
            embed_ok.add_field(name="✨ Passive thường trực", value="  ·  ".join(parts), inline=False)

        try:
            await inter.response.defer(ephemeral=True)
        except Exception:
            log.exception("Lỗi kho_do")
        await _refresh_kho_after_modal(inter, kv, embed_ok,
                                        footer_text=f"✨ Đã ghép {lc.get('ten', lq_id)}!")


class BanShopLQModal(discord.ui.Modal, title="Bán Lại Cho Shop"):
    sl_input = discord.ui.TextInput(
        label="Số lượng muốn bán", placeholder="1", default="1",
        min_length=1, max_length=5)

    def __init__(self, kho_view: "KhoDoView", item: dict, msg=None):
        super().__init__()
        self.kho_view = kho_view
        self.item     = item
        self.msg      = msg
        so_co = item.get("so_luong", 1)
        self.sl_input.placeholder = f"Tối đa: {so_co}"

    async def on_submit(self, inter: discord.Interaction):
        try:
            sl = max(1, int(self.sl_input.value))
        except (ValueError, TypeError):
            return await inter.response.send_message("❌ Số không hợp lệ!", ephemeral=True)
        ts    = await get_tu_si(inter.user.id)
        loai  = self.item.get("loai", "Linh Quả")
        lq_id = self.item["_lq_id"]
        db_key = "linh_qua" if loai == "Linh Quả" else "manh_linh_can"
        storage = ts.get(db_key, {})
        co = storage.get(lq_id, 0)
        if sl > co:
            return await inter.response.send_message(f"❌ Chỉ có **{co}**, không đủ **{sl}**!", ephemeral=True)

        # Tính giá 70%
        if loai == "Linh Quả":
            lq_data  = next((x for x in LINH_QUA if x["id"]==lq_id), None)
            gia_goc  = lq_data["gia"] if lq_data else 500
        else:
            gia_goc  = MANH_LINH_CAN_GIA.get(lq_id, 200)
        gia_nhan = int(gia_goc * 0.7) * sl

        new_storage = storage.copy()
        new_storage[lq_id] = co - sl
        if new_storage[lq_id] <= 0:
            del new_storage[lq_id]
        await update_tu_si(inter.user.id, **{db_key: new_storage})
        await add_linh_thach(inter.user.id, gia_nhan)

        # Refresh kho view
        kv = self.kho_view
        kv.ts    = await get_tu_si(inter.user.id)
        kv.items = _build_inventory(kv.ts)
        kv.sel_idx = min(kv.sel_idx, max(0, len(kv.items) - 1))
        kv._rebuild()
        try:
            await inter.response.defer(ephemeral=True)
        except Exception:
            log.exception("Lỗi kho_do")
        kho_embed = _embed_kho_trang(kv.ts, kv.user, kv.items, kv.trang)
        kho_embed.set_footer(text=f"✅ Đã bán {self.item['ten']} ×{sl} — +{fmt(gia_nhan)} LT")
        result_embed = discord.Embed(
            title="✅ Đã bán",
            description=f"Đã bán {self.item['ten']} — +{fmt(gia_nhan)} LT",
            color=0x57F287)
        await _refresh_kho_after_modal(inter, kv, result_embed,
                                        footer_text=f"✅ Đã bán {self.item['ten']} ×{sl} — +{fmt(gia_nhan)} LT")


class TreoBanLQModal(discord.ui.Modal, title="Treo Bán Phường Thị"):
    sl_input = discord.ui.TextInput(
        label="Số lượng muốn treo bán", placeholder="1", default="1",
        min_length=1, max_length=5)
    gia_input = discord.ui.TextInput(
        label="Giá/cái (Linh Thạch)",
        placeholder="Nhập giá bán...",
        min_length=1, max_length=12)

    def __init__(self, parent: "HoSoView", item: dict):
        super().__init__()
        self.parent = parent
        self.item   = item
        so_co = item.get("so_luong", 1)
        self.sl_input.placeholder = f"Tối đa: {so_co}"

    async def on_submit(self, inter: discord.Interaction):
        try:
            gia = int(self.gia_input.value.replace(",","").replace(".",""))
            sl  = max(1, int(self.sl_input.value))
        except (ValueError, TypeError):
            return await inter.response.send_message("❌ Số không hợp lệ!", ephemeral=True)
        if gia < 1:
            return await inter.response.send_message("❌ Giá phải lớn hơn 0!", ephemeral=True)

        await inter.response.defer(ephemeral=True)
        ts     = await get_tu_si(inter.user.id)
        loai   = self.item.get("loai", "Linh Quả")
        lq_id  = self.item["_lq_id"]
        db_key = "linh_qua" if loai == "Linh Quả" else "manh_linh_can"
        storage = ts.get(db_key, {})
        co = storage.get(lq_id, 0)
        if co < sl:
            return await safe_followup(inter, 
                f"❌ Chỉ có **{co}**, không đủ **{sl}**!", ephemeral=True)

        # Trừ khỏi túi
        new_storage = storage.copy()
        new_storage[lq_id] = co - sl
        if new_storage[lq_id] <= 0:
            del new_storage[lq_id]
        await update_tu_si(inter.user.id, **{db_key: new_storage})

        # Đăng lên phường thị — loại "lq" hoặc "manh"
        pt_loai = "lq" if loai == "Linh Quả" else "manh"
        pid = await dang_ban(inter.user.id, pt_loai, lq_id, sl, gia)
        await safe_followup(inter, 
            embed=discord.Embed(
                title="🏪 Treo bán thành công!",
                description=(
                    f"{self.item['emoji']} **{self.item['ten']}** ×{sl}\n"
                    f"Giá: **{fmt(gia)}** {E_LINH_THACH}/cái\n"
                    f"Mã phiên: **#{pid}**\n"
                    f"*(Người chơi toàn server có thể mua)*"
                ),
                color=0x5865F2),
            ephemeral=True)


def _resolve_phien_name(loai, iid, ikey):
    """Lấy tên + emoji item từ phiên chợ."""
    from utils.config import DAN_DUOC, NGUYEN_LIEU, LINH_QUA, LINH_CAN_BY_ID, MANH_LINH_CAN_EMOJI
    if loai == "dan_duoc" and iid < len(DAN_DUOC):
        return DAN_DUOC[iid]["emoji"], DAN_DUOC[iid]["ten"]
    elif loai == "dtl" and ikey:
        parts = ikey[4:].split(":",2)
        return "💊", parts[2] if len(parts)==3 else "Đan Tu Luyện"
    elif loai in ("lq", "manh") and ikey:
        lq = next((x for x in LINH_QUA if x["id"]==ikey), None)
        lc = LINH_CAN_BY_ID.get(ikey)
        if loai == "lq":
            return (lq["emoji"] if lq else "🌿"), (lq["ten"] if lq else ikey)
        else:
            emo = MANH_LINH_CAN_EMOJI.get(ikey, lq["emoji"] if lq else "🔶")
            name = f"Mảnh {lc['ten']}" if lc else f"Mảnh {ikey}"
            return emo, name
    elif iid < len(NGUYEN_LIEU):
        return NGUYEN_LIEU[iid]["emoji"], NGUYEN_LIEU[iid]["ten"]
    return "📦", f"Item {iid}"

class KhoDoView(discord.ui.View):
    # ── Tabs ──────────────────────────────────────────────────
    TAB_ALL   = "Tất Cả"
    TAB_NL    = "Nguyên Liệu"
    TAB_DAN   = "Đan Dược"
    TAB_PHAP  = "Pháp Bảo"
    TAB_LINH  = "Linh Căn & Mảnh"
    TAB_DTC   = "ĐP Thể Chất"

    TABS = [TAB_ALL, TAB_NL, TAB_DAN, TAB_PHAP, TAB_LINH, TAB_DTC]

    TAB_EMOJIS = {
        "Tất Cả": "📦", "Nguyên Liệu": "🪨", "Đan Dược": "💊",
        "Pháp Bảo": "⚔️", "Linh Căn & Mảnh": "🌿", "ĐP Thể Chất": "🧬",
    }
    TAB_LOAI = {
        "Nguyên Liệu":    ("Nguyên Liệu",),
        "Đan Dược":       ("Đan Tu Luyện", "Đan Dược"),
        "Pháp Bảo":       ("Pháp Bảo",),
        "Linh Căn & Mảnh": ("Linh Quả", "Mảnh Linh Căn"),
        "ĐP Thể Chất":    ("Nguyên Liệu ĐP TC",),
    }

    def __init__(self, parent: "HoSoView", user: discord.User, ts: dict[str, Any], items: list, actor_id: int = None):
        super().__init__(timeout=600)
        self.parent   = parent
        self.user     = user
        self.ts       = ts
        self.items    = items
        self.actor_id = actor_id or parent.owner_id  # người đang tương tác
        self.trang   = 0
        self.sel_idx = 0
        self.tab     = self.TAB_ALL
        self._rebuild()

    @property
    def filtered_items(self):
        if self.tab == self.TAB_ALL:
            return self.items
        loais = self.TAB_LOAI.get(self.tab, ())
        return [it for it in self.items if it.get("loai") in loais]

    def _total_pages(self):
        return max(1, (len(self.filtered_items) + ITEMS_PER_PAGE - 1) // ITEMS_PER_PAGE)

    def _page_items(self):
        start = self.trang * ITEMS_PER_PAGE
        return self.filtered_items[start : start + ITEMS_PER_PAGE]

    def _cur_item(self):
        fi = self.filtered_items
        return fi[self.sel_idx] if fi and 0 <= self.sel_idx < len(fi) else None

    def _rebuild(self):
        self.clear_items()
        total_page = self._total_pages()
        page_items = self._page_items()
        sel = self._cur_item()

        # Row 0: Dropdown item trên trang hiện tại
        if page_items:
            page_start = self.trang * ITEMS_PER_PAGE
            opts = []
            for i, it in enumerate(page_items):
                abs_idx = page_start + i
                label = f"{it['ten']} ×{it['so_luong']}"
                if it.get("loai") == "Mảnh Linh Căn":
                    label += f" ({it['so_luong']}/100)"
                elif it.get("_active"):
                    label += " ⚡"
                opts.append(discord.SelectOption(
                    label=label[:100],
                    value=str(abs_idx),
                    emoji=_parse_emoji(it["emoji"]) if it.get("emoji") else None,
                    default=(abs_idx == self.sel_idx),
                ))
            sel_dd = discord.ui.Select(
                placeholder="Chọn vật phẩm để xem / thao tác...",
                options=opts, row=0)
            sel_dd.callback = self._on_select
            self.add_item(sel_dd)

        # Row 1: Điều hướng
        fi = self.filtered_items
        btn_prev = discord.ui.Button(label="◀", style=discord.ButtonStyle.secondary, row=1,
                                     disabled=(not fi or self.trang == 0))
        btn_next = discord.ui.Button(label="▶", style=discord.ButtonStyle.secondary, row=1,
                                     disabled=(not fi or self.trang >= total_page - 1))
        btn_reload = discord.ui.Button(label="🔄 Làm mới", style=discord.ButtonStyle.primary, row=1)
        btn_detail = discord.ui.Button(label="📖 Chi tiết", style=discord.ButtonStyle.secondary, row=1,
                                       disabled=(not page_items))
        btn_prev.callback   = self._on_prev
        btn_next.callback   = self._on_next
        btn_reload.callback = self._on_reload
        btn_detail.callback = self._on_chi_giao
        self.add_item(btn_prev); self.add_item(btn_next)
        self.add_item(btn_reload); self.add_item(btn_detail)

        # Row 2: Hành động theo loại item
        if sel:
            loai = sel.get("loai", "")
            if loai == "Đan Tu Luyện" and sel.get("_dtl_gia", 0) > 0:
                gia_lai = int(sel["_dtl_gia"] * 0.6)
                b1 = discord.ui.Button(label=f"Bán lại ({fmt(gia_lai)} LT)",
                                       emoji=discord.PartialEmoji(name="LinhThach", id=1481645991181553796),
                                       style=discord.ButtonStyle.danger, row=2)
                b2 = discord.ui.Button(label="🏪 Treo bán Phường Thị",
                                       style=discord.ButtonStyle.success, row=2)
                b1.callback = self._on_ban_lai; b2.callback = self._on_treo_ban
                self.add_item(b1); self.add_item(b2)

            elif loai == "Đan Dược" and sel.get("_dd_gia", 0) > 0:
                gia_ban_lai = int(sel["_dd_gia"] * 0.6)
                b1 = discord.ui.Button(label=f"Bán lại ({fmt(gia_ban_lai)} LT)",
                                       emoji=discord.PartialEmoji(name="LinhThach", id=1481645991181553796),
                                       style=discord.ButtonStyle.danger, row=2)
                b1.callback = self._on_ban_lai
                self.add_item(b1)

            elif loai == "Linh Quả":
                _lq_data = next((x for x in LINH_QUA if x["id"] == sel.get("_lq_id")), None)
                _gia = int((_lq_data["gia"] if _lq_data else 500) * 0.7)
                b1 = discord.ui.Button(label="✨ Dùng linh quả",
                                       style=discord.ButtonStyle.primary, row=2)
                b2 = discord.ui.Button(label=f"Bán shop ({fmt(_gia)} LT/quả)",
                                       emoji=discord.PartialEmoji(name="LinhThach", id=1481645991181553796),
                                       style=discord.ButtonStyle.danger, row=2)
                b3 = discord.ui.Button(label="🏪 Treo bán", style=discord.ButtonStyle.success, row=2)
                b1.callback = self._on_dung_linh_qua
                b2.callback = self._on_ban_shop_lq
                b3.callback = self._on_treo_ban_lq
                self.add_item(b1); self.add_item(b2); self.add_item(b3)

            elif loai == "Mảnh Linh Căn":
                so_manh = sel.get("so_luong", 0)
                _gia = int(MANH_LINH_CAN_GIA.get(sel.get("_lq_id", ""), 200) * 0.7)
                b1 = discord.ui.Button(
                    label=f"🔮 Hợp thành ({so_manh}/100 mảnh)",
                    style=discord.ButtonStyle.primary, row=2,
                    disabled=(so_manh < 100))
                b2 = discord.ui.Button(label=f"Bán shop ({fmt(_gia)} LT/mảnh)",
                                       emoji=discord.PartialEmoji(name="LinhThach", id=1481645991181553796),
                                       style=discord.ButtonStyle.danger, row=2)
                b3 = discord.ui.Button(label="🏪 Treo bán", style=discord.ButtonStyle.success, row=2)
                b1.callback = self._on_hop_thanh
                b2.callback = self._on_ban_shop_lq
                b3.callback = self._on_treo_ban_lq
                self.add_item(b1); self.add_item(b2); self.add_item(b3)

            elif loai == "Pháp Bảo":
                is_active = sel.get("_active", False)
                btn_pb = discord.ui.Button(
                    label="✖ Gỡ trang bị" if is_active else "⚡ Trang bị",
                    style=discord.ButtonStyle.danger if is_active else discord.ButtonStyle.success,
                    row=2)
                btn_pb.callback = self._on_trang_bi_phap_bao
                self.add_item(btn_pb)

            # Nút Giao Dịch Riêng Tư — chỉ loại có thể trade
            if loai not in LOAI_BLOCK and sel.get("so_luong", 0) > 0:
                btn_trade = discord.ui.Button(
                    label="🤝 Giao Dịch",
                    style=discord.ButtonStyle.secondary,
                    row=2,
                )
                btn_trade.callback = self._on_private_trade
                self.add_item(btn_trade)

        # Row 3: Tab lọc với số lượng hiện tại
        def _cnt(tab):
            if tab == self.TAB_ALL: return len(self.items)
            ls = self.TAB_LOAI.get(tab, ())
            return sum(1 for it in self.items if it.get("loai") in ls)

        tab_opts = []
        for t in self.TABS:
            cnt = _cnt(t)
            lbl = f"{self.TAB_EMOJIS[t]} {t}" + (f"  ({cnt})" if cnt > 0 else "")
            tab_opts.append(discord.SelectOption(label=lbl[:100], value=t, default=(t == self.tab)))
        sel_tab = discord.ui.Select(placeholder="📂 Lọc theo loại vật phẩm...", options=tab_opts, row=3)
        sel_tab.callback = self._on_tab
        self.add_item(sel_tab)

        # Row 4: Quay lại
        btn_back = discord.ui.Button(label="◀ Quay Lại", style=discord.ButtonStyle.secondary, row=4)
        btn_back.callback = self._on_back
        self.add_item(btn_back)

    def _new_view(self) -> "KhoDoView":
        """Tạo KhoDoView mới với state hiện tại — tránh interaction failed sau rebuild."""
        nv = KhoDoView.__new__(KhoDoView)
        discord.ui.View.__init__(nv, timeout=self.timeout)
        nv.parent   = self.parent
        nv.user     = self.user
        nv.ts       = self.ts
        nv.items    = self.items
        nv.actor_id = self.actor_id
        nv.trang    = self.trang
        nv.sel_idx  = self.sel_idx
        nv.tab      = self.tab
        nv._rebuild()
        return nv

    # ── Callbacks ─────────────────────────────────────────────
    async def _on_select(self, inter: discord.Interaction):
        if inter.user.id != self.actor_id:
            return await inter.response.send_message("❌", ephemeral=True)
        self.sel_idx = min(int(inter.data["values"][0]), max(0, len(self.filtered_items) - 1))
        new_view = self._new_view(); self.stop()
        await inter.response.edit_message(
            embed=_embed_kho_trang(new_view.ts, new_view.user, new_view.filtered_items, new_view.trang,
                                   tab_label=f"{new_view.TAB_EMOJIS[new_view.tab]} {new_view.tab}"),
            view=new_view)

    async def _on_prev(self, inter: discord.Interaction):
        if inter.user.id != self.actor_id:
            return await inter.response.send_message("❌", ephemeral=True)
        self.trang = max(0, self.trang - 1)
        self.sel_idx = min(self.trang * ITEMS_PER_PAGE, max(0, len(self.filtered_items) - 1))
        new_view = self._new_view(); self.stop()
        await inter.response.edit_message(
            embed=_embed_kho_trang(new_view.ts, new_view.user, new_view.filtered_items, new_view.trang,
                                   tab_label=f"{new_view.TAB_EMOJIS[new_view.tab]} {new_view.tab}"),
            view=new_view)

    async def _on_next(self, inter: discord.Interaction):
        if inter.user.id != self.actor_id:
            return await inter.response.send_message("❌", ephemeral=True)
        self.trang = min(self._total_pages() - 1, self.trang + 1)
        self.sel_idx = min(self.trang * ITEMS_PER_PAGE, max(0, len(self.filtered_items) - 1))
        new_view = self._new_view(); self.stop()
        await inter.response.edit_message(
            embed=_embed_kho_trang(new_view.ts, new_view.user, new_view.filtered_items, new_view.trang,
                                   tab_label=f"{new_view.TAB_EMOJIS[new_view.tab]} {new_view.tab}"),
            view=new_view)

    async def _on_reload(self, inter: discord.Interaction):
        if inter.user.id != self.actor_id:
            return await inter.response.send_message("❌", ephemeral=True)
        self.ts    = await get_tu_si(inter.user.id)
        self.items = _build_inventory(self.ts)
        self.trang = min(self.trang, max(0, self._total_pages() - 1))
        self.sel_idx = min(self.trang * ITEMS_PER_PAGE, max(0, len(self.filtered_items) - 1))
        new_view = self._new_view(); self.stop()
        await inter.response.edit_message(
            embed=_embed_kho_trang(new_view.ts, new_view.user, new_view.filtered_items, new_view.trang,
                                   tab_label=f"{new_view.TAB_EMOJIS[new_view.tab]} {new_view.tab}"),
            view=new_view)

    async def _on_chi_giao(self, inter: discord.Interaction):
        if inter.user.id != self.actor_id:
            return await inter.response.send_message("❌", ephemeral=True)
        sel = self._cur_item()
        if not sel:
            return await inter.response.send_message("❌ Không có vật phẩm!", ephemeral=True)
        embed = discord.Embed(
            title=f"{sel['emoji']} {sel['ten']}",
            description=(
                f"**Số lượng:** {sel['so_luong']}\n"
                f"**Loại:** {sel['loai']}\n\n"
                f"{sel['mo_ta']}"
            ),
            color=0xFFD700)
        await inter.response.send_message(embed=embed, ephemeral=True)

    async def _on_tab(self, inter: discord.Interaction):
        if inter.user.id != self.actor_id:
            return await inter.response.send_message("❌", ephemeral=True)
        self.tab = inter.data["values"][0]
        self.trang = 0; self.sel_idx = 0
        new_view = self._new_view(); self.stop()
        await inter.response.edit_message(
            embed=_embed_kho_trang(new_view.ts, new_view.user, new_view.filtered_items, new_view.trang,
                                   tab_label=f"{new_view.TAB_EMOJIS[new_view.tab]} {new_view.tab}"),
            view=new_view)

    async def _on_dung_linh_qua(self, inter: discord.Interaction):
        if inter.user.id != self.actor_id:
            return await inter.response.send_message("❌", ephemeral=True)
        sel = self._cur_item()
        if not sel or sel.get("loai") not in ("Linh Quả", "Mảnh Linh Căn"):
            return await inter.response.send_message("❌ Không phải linh quả!", ephemeral=True)
        self._original_msg = inter.message
        await inter.response.send_modal(DungLinhQuaModal(self, sel))

    async def _on_ban_lai(self, inter: discord.Interaction):
        if inter.user.id != self.actor_id:
            return await inter.response.send_message("❌", ephemeral=True)
        sel = self._cur_item()
        if not sel or sel.get("loai") not in ("Đan Tu Luyện", "Đan Dược"):
            return await inter.response.send_message("❌ Không thể bán vật phẩm này!", ephemeral=True)
        await inter.response.send_modal(BanLaiModal(self, sel, msg=inter.message))

    async def _on_treo_ban(self, inter: discord.Interaction):
        if inter.user.id != self.actor_id:
            return await inter.response.send_message("❌", ephemeral=True)
        sel = self._cur_item()
        if not sel or sel.get("loai") != "Đan Tu Luyện":
            return await inter.response.send_message("❌ Không thể treo bán vật phẩm này!", ephemeral=True)
        await inter.response.send_modal(TreoBanDTLModal(self.parent, sel, sel.get("_dtl_gia", 0)))

    async def _on_treo_ban_lq(self, inter: discord.Interaction):
        if inter.user.id != self.actor_id:
            return await inter.response.send_message("❌", ephemeral=True)
        sel = self._cur_item()
        if not sel or sel.get("loai") not in ("Linh Quả", "Mảnh Linh Căn"):
            return await inter.response.send_message("❌", ephemeral=True)
        await inter.response.send_modal(TreoBanLQModal(self.parent, sel))

    async def _on_ban_shop_lq(self, inter: discord.Interaction):
        if inter.user.id != self.actor_id:
            return await inter.response.send_message("❌", ephemeral=True)
        sel = self._cur_item()
        if not sel or sel.get("loai") not in ("Linh Quả", "Mảnh Linh Căn"):
            return await inter.response.send_message("❌", ephemeral=True)
        self._original_msg = inter.message
        await inter.response.send_modal(BanShopLQModal(self, sel, msg=inter.message))

    async def _on_hop_thanh(self, inter: discord.Interaction):
        if inter.user.id != self.actor_id:
            return await inter.response.send_message("❌", ephemeral=True)
        sel = self._cur_item()
        if not sel or sel.get("loai") != "Mảnh Linh Căn":
            return await inter.response.send_message("❌", ephemeral=True)
        if sel.get("so_luong", 0) < 100:
            return await inter.response.send_message(
                f"❌ Cần **100 mảnh**, bạn chỉ có **{sel['so_luong']}**!", ephemeral=True)
        self._original_msg = inter.message
        await inter.response.send_modal(HopThanhModal(self, sel))

    async def _on_trang_bi_phap_bao(self, inter: discord.Interaction):
        if inter.user.id != self.actor_id:
            return await inter.response.send_message("❌", ephemeral=True)
        try:
            await inter.response.defer(ephemeral=True)
        except Exception:
            log.exception("Lỗi kho_do")
        sel = self._cur_item()
        if not sel or sel.get("loai") != "Pháp Bảo":
            return await safe_followup(inter, "❌ Chọn pháp bảo trước!", ephemeral=True)
        pb_id = sel["_pb_id"]; is_active = sel.get("_active", False)
        await update_tu_si(inter.user.id, phap_bao_active=(-1 if is_active else pb_id))
        self.ts = await get_tu_si(inter.user.id)
        self.items = _build_inventory(self.ts)
        pb = PHAP_BAO_BY_ID.get(pb_id)
        new_view = self._new_view(); self.stop()
        try:
            await inter.message.edit(
                embed=_embed_kho_trang(new_view.ts, new_view.user, new_view.filtered_items, new_view.trang,
                                       tab_label=f"{new_view.TAB_EMOJIS[new_view.tab]} {new_view.tab}"),
                view=new_view)
        except Exception:
            log.exception("Lỗi kho_do")
        await safe_followup(inter, 
            f"✖ Đã gỡ **{pb['ten']}**." if is_active else f"⚡ Đã trang bị **{pb['emoji']} {pb['ten']}**!",
            ephemeral=True)

    async def _on_private_trade(self, inter: discord.Interaction):
        if inter.user.id != self.actor_id:
            return await inter.response.send_message("❌", ephemeral=True)
        sel = self._cur_item()
        if not sel:
            return await inter.response.send_message("❌ Chọn vật phẩm trước!", ephemeral=True)
        if sel.get("loai") in LOAI_BLOCK:
            return await inter.response.send_message(
                f"❌ **{sel['loai']}** không hỗ trợ giao dịch riêng tư!", ephemeral=True)
        if sel.get("so_luong", 0) < 1:
            return await inter.response.send_message("❌ Không còn vật phẩm!", ephemeral=True)
        await inter.response.send_modal(PrivateTradeModal(self, sel))

    async def _on_back(self, inter: discord.Interaction):
        await _back_to_hoso(inter, self.parent)

class CuaHangView(discord.ui.View):
    def __init__(self, parent: "HoSoView", actor_id: int = None):
        super().__init__(timeout=120)
        self.parent   = parent
        self.actor_id = actor_id or parent.owner_id
        opts_dd = [
            discord.SelectOption(
                label=f"{d['ten']}  —  {fmt(d['gia'])} linh thạch",
                value=str(d["id"]),
                emoji=_parse_emoji(d["emoji"]),
                description=f"{CANH_GIOI[d['cg_yeu_cau']]['ten']} → {CANH_GIOI[d['cg_sau']]['ten']}" if d.get("cg_sau", 99) < len(CANH_GIOI) else d["mo_ta"])
            for d in DAN_DUOC if d.get("shop", True)]
        if opts_dd:
            sel_dd = discord.ui.Select(placeholder="Mua đan dược...", options=opts_dd, row=0)
            sel_dd.callback = self._buy_dd
            self.add_item(sel_dd)
        back = discord.ui.Button(label="◀ Quay Lại", style=discord.ButtonStyle.secondary, row=1)
        async def _do_back_1770(inter): await _back_to_hoso(inter, self.parent)
        back.callback = _do_back_1770
        self.add_item(back)

    async def _buy_dd(self, inter: discord.Interaction):
        if inter.user.id != self.actor_id:
            return await safe_followup(inter, "❌", ephemeral=True)
        await inter.response.send_modal(MuaDanModal(self.parent, int(inter.data["values"][0]), actor_id=self.actor_id))

    async def _buy_pb(self, inter: discord.Interaction):
        if inter.user.id != self.actor_id:
            return await safe_followup(inter, "❌", ephemeral=True)
        pb_id = int(inter.data["values"][0])
        ts    = await get_tu_si(inter.user.id)
        if pb_id < 0 or pb_id >= len(PHAP_BAO):
            return await safe_followup(inter, "❌ Pháp bảo không hợp lệ!", ephemeral=True)
        pb    = PHAP_BAO[pb_id]
        if pb_id in ts["phap_bao"]:
            return await safe_followup(inter, "❌ Đã sở hữu pháp bảo này!", ephemeral=True)
        if ts["linh_thach"] < pb["gia"]:
            return await safe_followup(inter, f"❌ Cần {fmt(pb['gia'])} {E_LINH_THACH}!", ephemeral=True)
        # Atomic: tránh double-spend khi click nhanh
        ok = await buy_phap_bao_atomic(inter.user.id, pb_id, pb["gia"], ts["phap_bao"] + [pb_id])
        if not ok:
            return await safe_followup(inter, "❌ Giao dịch thất bại — không đủ LT hoặc đã sở hữu!", ephemeral=True)
        await _back_to_hoso(inter, self.parent)
        await safe_followup(inter, 
            embed=e_ok(f"✅ Mua {pb['emoji']} {pb['ten']}!", f"{E_CONG_KICH}+{pb['at']}  {E_PHONG_NGU}+{pb['df']}  |  -{fmt(pb['gia'])} {E_LINH_THACH}"),
            ephemeral=True)


class MuaDanModal(discord.ui.Modal, title="Mua Đan Dược"):
    so_luong = discord.ui.TextInput(
        label="Số lượng", placeholder="1", default="1",
        min_length=1, max_length=3)
    def __init__(self, parent: "HoSoView", dan_id: int, actor_id: int = None):
        super().__init__()
        self.parent   = parent
        self.dan_id   = dan_id
        self.actor_id = actor_id or parent.owner_id

    async def on_submit(self, inter: discord.Interaction):
        try:    n = max(1, int(self.so_luong.value))
        except (ValueError, TypeError): return await inter.response.send_message("❌ Số không hợp lệ!", ephemeral=True)
        ts    = await get_tu_si(inter.user.id)
        dan   = DAN_DUOC[self.dan_id]
        total = dan["gia"] * n
        if ts["linh_thach"] < total:
            return await inter.response.send_message(f"❌ Cần {fmt(total)} {E_LINH_THACH}!", ephemeral=True)
        dd = ts["dan_duoc"].copy()
        dd[str(self.dan_id)] = dd.get(str(self.dan_id), 0) + n
        await add_linh_thach(inter.user.id, -total)
        await update_tu_si(inter.user.id, dan_duoc=dd)
        # Respond modal trước (bắt buộc), sau đó edit message gốc qua followup
        try:
            await inter.response.defer()
        except Exception:
            log.exception("Lỗi kho_do")
        await safe_followup(inter, 
            embed=e_ok(f"✅ Mua {dan['emoji']} {dan['ten']} ×{n}", f"-{fmt(total)} {E_LINH_THACH}"),
            ephemeral=True)
        # Update lại hoso message gốc
        is_own = (inter.user.id == self.actor_id)
        if is_own:
            await self.parent._reload(inter.user.id)
            self.parent._rebuild()
            try:
                await inter.edit_original_response(embed=self.parent._current_embed(), view=self.parent)
            except Exception:
                log.exception("Lỗi kho_do")


# ══════════════════════════════════════════════════════════════
#  PHƯỜNG THỊ VIEW
# ══════════════════════════════════════════════════════════════
class PhuongThiView(discord.ui.View):
    PT_PER_PAGE = 8

    def __init__(self, parent: "HoSoView", items: list = None, page: int = 0, actor_id: int = None):
        super().__init__(timeout=120)
        self.parent   = parent
        self.items    = items or []
        self.page     = page
        self.actor_id = actor_id or parent.owner_id
        total_pages = max(1, (len(self.items) + self.PT_PER_PAGE - 1) // self.PT_PER_PAGE)

        btn_prev   = discord.ui.Button(label="◀", style=discord.ButtonStyle.secondary,
                                       row=0, disabled=(page == 0))
        btn_next   = discord.ui.Button(label="▶", style=discord.ButtonStyle.secondary,
                                       row=0, disabled=(page >= total_pages - 1))
        btn_buy    = discord.ui.Button(label="🛒 Mua (nhập mã #)", style=discord.ButtonStyle.primary,   row=1)
        btn_reload = discord.ui.Button(label="🔄 Tải lại",         style=discord.ButtonStyle.primary,   row=1)
        btn_myitem = discord.ui.Button(label="📦 Đồ của tôi",      style=discord.ButtonStyle.secondary, row=1)
        btn_cancel = discord.ui.Button(label="🗑️ Hủy bán",         style=discord.ButtonStyle.danger,    row=1)
        btn_back   = discord.ui.Button(label="◀ Quay Lại",         style=discord.ButtonStyle.secondary, row=2)

        btn_prev.callback   = self._prev_page
        btn_next.callback   = self._next_page
        btn_buy.callback    = self._buy
        btn_reload.callback = self._reload
        btn_myitem.callback = self._my_items
        btn_cancel.callback = self._cancel
        async def _do_back_pt(inter): await _back_to_hoso(inter, self.parent)
        btn_back.callback = _do_back_pt

        self.add_item(btn_prev)
        self.add_item(btn_next)
        self.add_item(btn_buy)
        self.add_item(btn_reload)
        self.add_item(btn_myitem)
        self.add_item(btn_cancel)
        self.add_item(btn_back)

    async def _prev_page(self, inter: discord.Interaction):
        await self._go_page(inter, self.page - 1)

    async def _next_page(self, inter: discord.Interaction):
        await self._go_page(inter, self.page + 1)

    async def _go_page(self, inter: discord.Interaction, new_page: int):
        try:
            await inter.response.defer(ephemeral=True)
        except Exception:
            log.exception("Lỗi kho_do")
        from cogs.hoso import _build_phuong_thi_embed
        items = await get_phien_cho(da_ban=False)
        embed, f_pt = await _build_phuong_thi_embed(items, page=new_page)
        view = PhuongThiView(self.parent, items=items, page=new_page, actor_id=self.actor_id)
        if f_pt:
            await inter.edit_original_response(embed=embed, attachments=[f_pt], view=view)
        else:
            await inter.edit_original_response(embed=embed, attachments=[], view=view)

    async def _buy(self, inter: discord.Interaction):
        if inter.user.id != self.actor_id:
            return await inter.response.send_message("❌", ephemeral=True)
        await inter.response.send_modal(MuaPhienModal(self.parent))

    async def _reload(self, inter: discord.Interaction):
        await self._go_page(inter, 0)

    async def _my_items(self, inter: discord.Interaction):
        if inter.user.id != self.actor_id:
            return await inter.response.send_message("❌", ephemeral=True)
        try:
            await inter.response.defer(ephemeral=True)
        except Exception:
            log.exception("Lỗi kho_do")
        import time as _t
        EXPIRE_SECS = 172800  # 2 ngày
        items = await get_phien_cho(da_ban=False)
        mine  = [ph for ph in items if ph["nguoi_ban"] == inter.user.id]
        if not mine:
            return await safe_followup(inter, "*(Bạn chưa đăng bán vật phẩm nào)*", ephemeral=True)
        lines = []
        for ph in mine:
            loai = ph["loai"]; iid = ph["item_id"]; ikey = ph.get("item_key","")
            _, name = _resolve_phien_name(loai, iid, ikey)
            remaining = (ph["thoi_gian"] + EXPIRE_SECS) - int(_t.time())
            if remaining <= 0:
                expire_tag = " ❌ *hết hạn*"
            elif remaining <= 3600:
                expire_tag = " ⚠️ *còn <1h*"
            else:
                h = remaining // 3600
                d = h // 24
                expire_tag = f" ⏰ còn {d}ngày {h%24}h" if d > 0 else f" ⏰ còn {h}h"
            lines.append(f"#{ph['id']} **{name}** ×{ph['so_luong']} — {fmt(ph['gia'])} LT/cái{expire_tag}")
        embed = discord.Embed(title="📦 Vật phẩm đang treo bán",
            description="\n".join(lines), color=0xC47A2B)
        embed.set_footer(text="Phiên hết hạn sau 2 ngày — item hoàn trả tự động qua DM")
        await safe_followup(inter, embed=embed, ephemeral=True)

    async def _cancel(self, inter: discord.Interaction):
        if inter.user.id != self.actor_id:
            return await inter.response.send_message("❌", ephemeral=True)
        await inter.response.send_modal(HuyBanModal(self.parent))


class MuaPhienModal(discord.ui.Modal, title="Mua Phiên Chợ"):
    phien_id = discord.ui.TextInput(
        label="Mã phiên (#)", placeholder="12",
        min_length=1, max_length=6)
    def __init__(self, parent: "HoSoView"):
        super().__init__()
        self.parent = parent

    async def on_submit(self, inter: discord.Interaction):
        await inter.response.defer(ephemeral=True)
        try:    pid = int(self.phien_id.value.lstrip("#"))
        except (ValueError, TypeError): return await safe_followup(inter, "❌ Mã không hợp lệ!", ephemeral=True)
        ph = await get_phien_cho_item(pid)
        if not ph or ph["da_ban"]:
            return await safe_followup(inter, "❌ Phiên không tồn tại hoặc đã bán!", ephemeral=True)
        if ph["nguoi_ban"] == inter.user.id:
            return await safe_followup(inter, "❌ Không tự mua của mình!", ephemeral=True)
        ts = await get_tu_si(inter.user.id)
        tong_gia = ph["gia"] * ph["so_luong"]
        if ts["linh_thach"] < tong_gia:
            return await safe_followup(inter, 
                f"❌ Cần **{fmt(tong_gia)}** {E_LINH_THACH} ({fmt(ph['gia'])}/cái × {ph['so_luong']})!", ephemeral=True)

        # Atomic: đánh dấu đã bán trước — nếu thất bại nghĩa là người khác đã mua trước
        ok = await mua_phien_cho(pid)
        if not ok:
            return await safe_followup(inter, "❌ Phiên vừa được người khác mua mất rồi!", ephemeral=True)

        loai = ph["loai"]; iid = ph["item_id"]; sl = ph["so_luong"]
        ikey = ph.get("item_key", "")
        # Dùng add_linh_thach atomic thay vì ts cũ — tránh race condition LT sai
        await add_linh_thach(inter.user.id, -tong_gia)
        ts2 = await get_tu_si(inter.user.id)
        if loai == "dan_duoc":
            dd = ts2["dan_duoc"].copy(); dd[str(iid)] = dd.get(str(iid), 0) + sl
            await update_tu_si(inter.user.id, dan_duoc=dd)
        elif loai == "dtl" and ikey:
            dd = ts2["dan_duoc"].copy(); dd[ikey] = dd.get(ikey, 0) + sl
            await update_tu_si(inter.user.id, dan_duoc=dd)
        elif loai == "lq" and ikey:
            lq = ts2.get("linh_qua", {}).copy(); lq[ikey] = lq.get(ikey, 0) + sl
            await update_tu_si(inter.user.id, linh_qua=lq)
        elif loai == "manh" and ikey:
            manh = ts2.get("manh_linh_can", {}).copy(); manh[ikey] = manh.get(ikey, 0) + sl
            await update_tu_si(inter.user.id, manh_linh_can=manh)
        else:
            nl = ts2["nguyen_lieu"].copy(); nl[str(iid)] = nl.get(str(iid), 0) + sl
            await update_tu_si(inter.user.id, nguyen_lieu=nl)
        await add_linh_thach(ph["nguoi_ban"], tong_gia)
        emo, name = _resolve_phien_name(loai, iid, ikey)

        # Ghi log giao dịch
        await log_giao_dich(
            "phien_cho",
            sender_id=ph["nguoi_ban"],
            receiver_id=inter.user.id,
            item_name=f"{emo} {name}",
            so_luong=sl,
            gia_lt=tong_gia,
            ghi_chu=f"pid={pid}",
        )

        # DM người bán
        try:
            ts_buyer  = await get_tu_si(inter.user.id)
            ts_seller = await get_tu_si(ph["nguoi_ban"])
            buyer_name  = ts_buyer["dao_hieu"]  if ts_buyer  else inter.user.display_name
            seller_new_lt = (ts_seller["linh_thach"] + tong_gia) if ts_seller else tong_gia
            seller_user = inter.client.get_user(ph["nguoi_ban"]) or await inter.client.fetch_user(ph["nguoi_ban"])
            if seller_user:
                dm_embed = discord.Embed(
                    title="🏪 Phường Thị — Giao Dịch Thành Công!",
                    description=(
                        "**" + buyer_name + "** vừa mua **" + name + " ×" + str(sl) + "** của bạn.\n\n"
                        f"{E_LINH_THACH} Bạn nhận được: **+{fmt(tong_gia)}** Linh Thạch\n"
                        "💼 Số dư hiện tại: **" + fmt(seller_new_lt) + "** Linh Thạch"
                    ),
                    color=0x57F287)
                await seller_user.send(embed=dm_embed)
        except discord.HTTPException:
            pass  # DM thất bại (user tắt DM) không ảnh hưởng giao dịch

        await safe_followup(inter, 
            f"✅ Mua **{name} ×{sl}** thành công!  -{fmt(tong_gia)} LT",
            ephemeral=True)



class DungLinhQuaModal(discord.ui.Modal, title="Dùng Linh Quả"):
    so_luong = discord.ui.TextInput(
        label="Số lượng dùng (tối đa 100)",
        placeholder="1", min_length=1, max_length=3)

    def __init__(self, kho_view: "KhoDoView", item: dict):
        super().__init__()
        self.kho_view = kho_view
        self.item     = item
        co = item.get("so_luong", 0)
        self.so_luong.placeholder = f"Tối đa: {min(co, 100)}"

    async def on_submit(self, inter: discord.Interaction):
        try:
            sl = max(1, int(self.so_luong.value))
        except (ValueError, TypeError):
            return await inter.response.send_message("❌ Số không hợp lệ!", ephemeral=True)
        sl = min(sl, 100)

        lq_id = self.item.get("_lq_id")
        if not lq_id:
            return await inter.response.send_message("❌ Lỗi item!", ephemeral=True)

        lq = LINH_QUA_BY_ID.get(lq_id)
        lc = LINH_CAN_BY_ID.get(lq_id)
        if not lq or not lc:
            return await inter.response.send_message("❌ Linh quả không hợp lệ!", ephemeral=True)

        ts = await get_tu_si(inter.user.id)
        loai_item = self.item.get("loai", "Linh Quả")
        co = ts.get("linh_qua" if loai_item == "Linh Quả" else "manh_linh_can", {}).get(lq_id, 0)
        if sl > co:
            return await inter.response.send_message(
                f"❌ Chỉ có **{co}** {lq['ten']}!", ephemeral=True)

        lc_owned  = lq_id in ts.get("linh_can_so_huu", [])
        diem_them = sl * lq["diem"]

        # Defer sau validation — tránh timeout 3s
        try:
            await inter.response.defer(ephemeral=True)
        except Exception:
            log.exception("Lỗi kho_do")

        # Trừ từ đúng field
        if loai_item == "Linh Quả":
            field_new = ts.get("linh_qua", {}).copy()
        else:
            field_new = ts.get("manh_linh_can", {}).copy()
        field_new[lq_id] = co - sl
        if field_new[lq_id] <= 0:
            del field_new[lq_id]

        if lc_owned and loai_item == "Linh Quả":
            # Linh quả → tăng điểm linh căn
            diem_cu  = ts.get("linh_can_diem", {}).get(lq_id, 0)
            diem_moi = diem_cu + diem_them
            diem_new = ts.get("linh_can_diem", {}).copy()
            diem_new[lq_id] = diem_moi
            await update_tu_si(inter.user.id,
                linh_qua=field_new, linh_can_diem=diem_new)
            lop_moi = _check_lop_moi(diem_cu, diem_moi)
            # Map lớp → tên cảnh giới để thông báo rõ hơn
            _CG_NAMES = ["Luyện Khí","Trúc Cơ","Kết Tinh","Kim Đan","Cụ Linh",
                         "Nguyên Anh","Hóa Thần","Ngộ Đạo","Vũ Hóa","Đăng Tiên"]
            lop_str = ""
            for lop in lop_moi:
                cg_name = _CG_NAMES[lop] if lop < len(_CG_NAMES) else f"CG{lop}"
                lop_str += (
                    f"\n🌟 **Buff {lc['ten']} lớp {lop} kích hoạt!**"
                    f"\n*(Đã đủ điểm ngưỡng {cg_name} — passive thêm 1 lần)*"
                )
            embed = discord.Embed(
                title=f"✨ {lc['emoji']} {lc['ten']} — Buff Lớp Mới!" if lop_moi else f"{lq['emoji']} Dùng {lq['ten']}",
                description=(
                    f"Đã dùng **{sl}** {lq['ten']}.\n"
                    f"Điểm **{lc['ten']}**: {diem_cu:,} → **{diem_moi:,}**"
                    + lop_str
                ),
                color=0xFFD700 if lop_moi else lc["mau"])
        elif loai_item == "Linh Quả":
            # Linh quả nhưng chưa có căn — không xử lý ở đây
            await safe_followup(inter, 
                "❌ Chỉ dùng linh quả khi đã sở hữu linh căn tương ứng!", ephemeral=True)
            return
        else:
            # Mảnh linh căn → ghép căn mới
            manh_hien = field_new.get(lq_id, 0)
            ghep_duoc = manh_hien // 100
            if ghep_duoc > 0:
                # Kiểm tra: đã có căn này rồi → block
                MAX_LINH_CAN = 9
                lc_so_huu_cur  = ts.get("linh_can_so_huu", [])
                da_co_can_nay  = lq_id in lc_so_huu_cur
                so_unique_hien = len(set(lc_so_huu_cur))
                if da_co_can_nay:
                    await safe_followup(inter, 
                        f"❌ Đã sở hữu **{lc['ten']}**! Mỗi loại linh căn chỉ ghép được 1 lần.",
                        ephemeral=True)
                    return
                if so_unique_hien >= MAX_LINH_CAN:
                    await safe_followup(inter, 
                        f"❌ Đã đạt giới hạn **{MAX_LINH_CAN} loại linh căn**! Không thể ghép thêm.",
                        ephemeral=True)
                    return
                field_new[lq_id] = manh_hien % 100
                if field_new[lq_id] == 0:
                    del field_new[lq_id]
                lc_so_huu = ts.get("linh_can_so_huu", []).copy()
                lc_so_huu.append(lq_id)
                diem_new = ts.get("linh_can_diem", {}).copy()
                diem_new[lq_id] = 0
                await update_tu_si(inter.user.id,
                    manh_linh_can=field_new,
                    linh_can_so_huu=lc_so_huu,
                    linh_can_diem=diem_new)
                embed = discord.Embed(
                    title=f"✨ GHÉP LINH CĂN THÀNH CÔNG!",
                    description=(
                        f"{lq['emoji']} **{lc['ten']}** đã được giác tỉnh!\n\n"
                        f"*{lc['chuc_mung']}*"
                    ),
                    color=lc["mau"])
                p = lc.get("passive", {})
                _PASSIVE_LABEL = {
                    "at_flat":   f"{E_CONG_KICH} Tấn Công",
                    "at_pct":    f"{E_CONG_KICH} Tấn Công",
                    "df_flat":   f"{E_PHONG_NGU} Phòng Ngự",
                    "def_pct":   f"{E_PHONG_NGU} Phòng Ngự",
                    "hp_flat":   f"{E_SINH_LUC} Sinh Lực",
                    "hp_pct":    f"{E_SINH_LUC} Sinh Lực",
                    "hoi_tam":   f"{E_HOI_TAM} Hội Tâm",
                    "ho_tam":    f"{E_HO_TAM} Hộ Tâm",
                    "bao_kich":  f"{E_BAO_KICH} Bạo Kích",
                    "khang_bao": f"{E_KHANG_BAO} Kháng Bạo",
                    "drop_rate": "🍀 Drop%",
                    "exp_pct":   f"{E_TU_VI} Tu Vi",
                }
                passive_parts = []
                for k, v in p.items():
                    label = _PASSIVE_LABEL.get(k, k)
                    if k in ("hoi_tam", "ho_tam", "at_flat", "df_flat", "hp_flat"):
                        passive_parts.append(f"{label} **+{v}**")
                    else:
                        passive_parts.append(f"{label} **+{v}%**")
                if passive_parts:
                    embed.add_field(name="✨ Passive thường trực",
                        value="\n".join(passive_parts), inline=False)
            else:
                # Chỉ tích lũy mảnh
                await update_tu_si(inter.user.id, manh_linh_can=field_new)
                tong = field_new.get(lq_id, 0)
                embed = discord.Embed(
                    title=f"{lq['emoji']} Tích lũy mảnh linh căn",
                    description=(
                        f"Đã dùng **{sl}** mảnh **{lq['ten']}**.\n"
                        f"Tiến độ: **{tong}/100** mảnh để ghép **{lc['ten']}**"
                    ),
                    color=0x888888)

        # Refresh kho view
        kv = self.kho_view
        kv.ts    = await get_tu_si(inter.user.id)
        kv.items = _build_inventory(kv.ts)
        kv.sel_idx = min(kv.sel_idx, max(0, len(kv.items) - 1))
        kv._rebuild()
        await _refresh_kho_after_modal(inter, kv, embed)


class HuyBanModal(discord.ui.Modal, title="Hủy Bán Phường Thị"):
    phien_id = discord.ui.TextInput(
        label="Mã phiên cần hủy (#)", placeholder="12",
        min_length=1, max_length=6)

    def __init__(self, parent):
        super().__init__()
        self.parent = parent

    async def on_submit(self, inter: discord.Interaction):
        try:
            pid = int(self.phien_id.value.lstrip("#"))
        except (ValueError, TypeError):
            return await inter.response.send_message("❌ Mã không hợp lệ!", ephemeral=True)

        await inter.response.defer(ephemeral=True)
        ph = await get_phien_cho_item(pid)
        if not ph or ph["da_ban"]:
            return await safe_followup(inter, "❌ Phiên không tồn tại hoặc đã bán rồi!", ephemeral=True)
        if ph["nguoi_ban"] != inter.user.id:
            return await safe_followup(inter, "❌ Đây không phải phiên của bạn!", ephemeral=True)

        ok = await cancel_phien_cho(pid, inter.user.id)
        if not ok:
            return await safe_followup(inter, "❌ Hủy thất bại — phiên có thể vừa được mua!", ephemeral=True)

        # Hoàn trả item về túi
        ts = await get_tu_si(inter.user.id)
        loai = ph["loai"]; iid = ph["item_id"]; sl = ph["so_luong"]; ikey = ph.get("item_key", "")
        _, name = _resolve_phien_name(loai, iid, ikey)
        if loai == "dan_duoc":
            dd = ts["dan_duoc"].copy(); dd[str(iid)] = dd.get(str(iid), 0) + sl
            await update_tu_si(inter.user.id, dan_duoc=dd)
        elif loai == "dtl" and ikey:
            dd = ts["dan_duoc"].copy(); dd[ikey] = dd.get(ikey, 0) + sl
            await update_tu_si(inter.user.id, dan_duoc=dd)
        elif loai == "lq" and ikey:
            lq = ts.get("linh_qua", {}).copy(); lq[ikey] = lq.get(ikey, 0) + sl
            await update_tu_si(inter.user.id, linh_qua=lq)
        elif loai == "manh" and ikey:
            manh = ts.get("manh_linh_can", {}).copy(); manh[ikey] = manh.get(ikey, 0) + sl
            await update_tu_si(inter.user.id, manh_linh_can=manh)
        else:
            nl = ts["nguyen_lieu"].copy(); nl[str(iid)] = nl.get(str(iid), 0) + sl
            await update_tu_si(inter.user.id, nguyen_lieu=nl)

        await safe_followup(inter, 
            f"✅ Đã hủy phiên **#{pid}** — hoàn trả **{name} ×{sl}** về túi!",
            ephemeral=True)

class DangBanModal(discord.ui.Modal, title="Đăng Bán Phường Thị"):
    loai_f = discord.ui.TextInput(label="Loại (dan_duoc / nguyen_lieu)", placeholder="dan_duoc")
    id_f   = discord.ui.TextInput(label="ID vật phẩm", placeholder="0", max_length=2)
    sl_f   = discord.ui.TextInput(label="Số lượng", placeholder="1", max_length=4)
    gia_f  = discord.ui.TextInput(label="Giá (Linh Thạch)", placeholder="100", max_length=10)
    def __init__(self, parent: "HoSoView"):
        super().__init__()
        self.parent = parent

    async def on_submit(self, inter: discord.Interaction):
        loai = self.loai_f.value.strip()
        if loai not in ("dan_duoc", "nguyen_lieu"):
            return await inter.response.send_message("❌ Loại phải là: dan_duoc hoặc nguyen_lieu", ephemeral=True)
        try:
            iid = int(self.id_f.value)
            sl  = int(self.sl_f.value)
            gia = int(self.gia_f.value)
        except (ValueError, TypeError):
            return await inter.response.send_message("❌ Số không hợp lệ!", ephemeral=True)
        await inter.response.defer(ephemeral=True)
        ts = await get_tu_si(inter.user.id)
        if loai == "dan_duoc":
            if iid >= len(DAN_DUOC): return await safe_followup(inter, "❌ ID sai!", ephemeral=True)
            have = ts["dan_duoc"].get(str(iid), 0)
            if have < sl: return await safe_followup(inter, f"❌ Chỉ có {have} cái!", ephemeral=True)
            dd = ts["dan_duoc"].copy(); dd[str(iid)] -= sl
            if dd[str(iid)] <= 0: del dd[str(iid)]
            await update_tu_si(inter.user.id, dan_duoc=dd)
            item_name = DAN_DUOC[iid]["ten"]
        else:
            if iid >= len(NGUYEN_LIEU): return await safe_followup(inter, "❌ ID sai!", ephemeral=True)
            have = ts["nguyen_lieu"].get(str(iid), 0)
            if have < sl: return await safe_followup(inter, f"❌ Chỉ có {have} cái!", ephemeral=True)
            nl = ts["nguyen_lieu"].copy(); nl[str(iid)] -= sl
            if nl[str(iid)] <= 0: del nl[str(iid)]
            await update_tu_si(inter.user.id, nguyen_lieu=nl)
            item_name = NGUYEN_LIEU[iid]["ten"]
        pid = await dang_ban(inter.user.id, loai, iid, sl, gia)
        await safe_followup(inter, 
            f"✅ Đăng bán **{item_name} ×{sl}** giá **{fmt(gia)} {E_LINH_THACH}**  —  Mã: **#{pid}**",
            ephemeral=True)


# ══════════════════════════════════════════════════════════════
#  YÊU THÚ VIEW
# ══════════════════════════════════════════════════════════════
