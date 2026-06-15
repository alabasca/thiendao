"""
╔══════════════════════════════════════════════════════╗
║  QUAN HỆ — Tặng Quà & Kết Giao                      ║
╚══════════════════════════════════════════════════════╝
"""
from __future__ import annotations

import discord
import logging

log = logging.getLogger("quan_he")

from utils.config import (
    DAN_DUOC, EMOJI_DAN_DUOC,
    QUAN_HE_MOC_DUONG, QUAN_HE_LOAI,
    TANG_QUA_DIEM_MAX_NGAY, TANG_QUA_LT_MAX,
    TANG_QUA_LT_PER_DIEM, TANG_QUA_DAN_PER_DIEM,
    get_quan_he_cap, fmt,
)
from utils.embeds import e_ok, e_loi, e_warn, e_info
from utils.database import (
    get_tu_si, update_tu_si, add_linh_thach,
    get_quan_he, upsert_quan_he, set_quan_he_loai,
    get_tang_qua_hom_nay, add_tang_qua_log,
    log_giao_dich,
)
from utils.bot_emojis import E_LINH_THACH, E_DAN_DUOC
import re as _re
from utils.embeds import safe_followup
from cogs.views._common import _back_to_hoso

def _parse_emoji(s: str):
    m = _re.match(r"<a?:(\w+):(\d+)>", s)
    if m:
        return discord.PartialEmoji(name=m.group(1), id=int(m.group(2)))
    return s


# ══════════════════════════════════════════════════════
#  EMBED QUAN HỆ
# ══════════════════════════════════════════════════════
def _embed_quan_he(
    ts_viewer: dict,
    ts_target: dict,
    user_viewer: discord.User,
    user_target: discord.User,
    qh: dict | None,
) -> discord.Embed:
    diem = qh["diem"] if qh else 0
    cap  = get_quan_he_cap(diem)

    embed = discord.Embed(
        title=f"{cap['emoji']} Quan Hệ",
        color=0xE91E8C if diem >= 0 else 0x7B2FBE,
    )
    embed.set_author(name=user_viewer.display_name, icon_url=user_viewer.display_avatar.url)
    embed.set_thumbnail(url=user_target.display_avatar.url)

    embed.add_field(
        name="🎯 Đối Tượng",
        value=f"**{user_target.display_name}**\n*{ts_target.get('dao_hieu','Vô Danh')}*",
        inline=True,
    )
    embed.add_field(
        name="❤️ Điểm Quan Hệ",
        value=f"**{diem:+d}** điểm\n*{cap['ten']}*",
        inline=True,
    )

    # Kết giao hiện tại
    loai = qh["loai"] if qh else ""
    if loai and loai in QUAN_HE_LOAI:
        kl = QUAN_HE_LOAI[loai]
        embed.add_field(
            name="💞 Kết Giao",
            value=f"{kl['emoji']} **{kl['ten']}**",
            inline=True,
        )

    # Mốc tiếp theo
    moc_tiep = None
    for m in QUAN_HE_MOC_DUONG:
        if diem < m["diem"]:
            moc_tiep = m
            break
    if moc_tiep:
        con_lai = moc_tiep["diem"] - diem
        embed.add_field(
            name="⬆️ Mốc Tiếp Theo",
            value=f"{moc_tiep['emoji']} **{moc_tiep['ten']}** — còn **{con_lai}** điểm",
            inline=False,
        )

    embed.set_footer(text="Tặng quà để tăng điểm quan hệ • Tối đa 100đ/ngày")
    return embed


# ══════════════════════════════════════════════════════
#  TẶNG QUÀ MODAL — Linh Thạch
# ══════════════════════════════════════════════════════

async def _dm_tang_qua(bot, target_id: int, sender_dao_hieu: str,
                       loai_qua: str, so_luong: str, diem_delta: int, diem_total: int):
    """Gửi DM cho người được nhận quà."""
    cap = get_quan_he_cap(diem_total)
    try:
        user = await bot.fetch_user(target_id)
        embed = discord.Embed(
            title="🎁 Bạn nhận được quà!",
            description=(
                f"**{sender_dao_hieu}** vừa tặng bạn **{so_luong} {loai_qua}**\n\n"
                f"❤️ Quan hệ tăng thêm **+{diem_delta}** điểm\n"
                f"Tổng điểm quan hệ: **{diem_total:+d}** — *{cap['ten']}*"
            ),
            color=0xFF69B4
        )
        embed.set_footer(text="Dùng /hoso → Quan Hệ để xem chi tiết")
        await user.send(embed=embed)
    except discord.HTTPException:
        pass  # User tắt DM hoặc không tìm thấy — bỏ qua

class TangLinhThachModal(discord.ui.Modal, title="✨ Tặng Linh Thạch"):
    so_luong = discord.ui.TextInput(
        label="Số linh thạch muốn tặng",
        placeholder=f"Tối đa 10.000 LT/ngày (100 LT = 1 điểm QH)",
        required=True,
        max_length=6,
    )

    def __init__(self, parent: "TangQuaView"):
        super().__init__()
        self.view_parent = parent

    async def on_submit(self, inter: discord.Interaction):
        try:
            so = int(self.so_luong.value.strip())
        except ValueError:
            return await inter.response.send_message(
                embed=e_loi("❌ Lỗi", "Vui lòng nhập số hợp lệ!"), ephemeral=True)

        if so <= 0:
            return await inter.response.send_message(
                embed=e_loi("❌ Lỗi", "Số linh thạch phải > 0!"), ephemeral=True)
        if so > TANG_QUA_LT_MAX:
            return await inter.response.send_message(
                embed=e_warn("⚠️ Vượt Giới Hạn", f"Tối đa **{fmt(TANG_QUA_LT_MAX)} LT** mỗi lần!"),
                ephemeral=True)

        await inter.response.defer(ephemeral=True)
        viewer_id = inter.user.id
        target_id = self.view_parent.ts_target["user_id"]

        # Kiểm tra LT người tặng
        ts_viewer = await get_tu_si(viewer_id)
        if ts_viewer["linh_thach"] < so:
            return await safe_followup(inter, 
                embed=e_loi("❌ Không Đủ Linh Thạch", f"Bạn chỉ có **{fmt(ts_viewer['linh_thach'])} LT**!"),
                ephemeral=True)

        # Kiểm tra giới hạn ngày
        da_tang_hom_nay = await get_tang_qua_hom_nay(viewer_id, target_id)
        con_lai_diem    = TANG_QUA_DIEM_MAX_NGAY - da_tang_hom_nay
        if con_lai_diem <= 0:
            return await safe_followup(inter, 
                embed=e_warn("⏳ Đã Đạt Giới Hạn", "Bạn đã tặng đủ **100 điểm QH** hôm nay cho người này!"),
                ephemeral=True)

        # Tính điểm thực tế (giới hạn theo còn lại ngày + max LT)
        diem_tu_so_lt  = so // TANG_QUA_LT_PER_DIEM
        diem_thuc_te   = min(diem_tu_so_lt, con_lai_diem)
        lt_thuc_te     = diem_thuc_te * TANG_QUA_LT_PER_DIEM

        if lt_thuc_te <= 0:
            return await safe_followup(inter, 
                embed=e_warn("⚠️ Quá Ít", f"Cần ít nhất **{TANG_QUA_LT_PER_DIEM} LT** để tặng!"),
                ephemeral=True)

        # Thực hiện giao dịch
        await add_linh_thach(viewer_id, -lt_thuc_te)
        await add_linh_thach(target_id,  lt_thuc_te)
        qh = await upsert_quan_he(viewer_id, target_id, diem_delta=diem_thuc_te)
        await add_tang_qua_log(viewer_id, target_id, diem_thuc_te)
        await log_giao_dich(
            "tang_lt",
            sender_id=viewer_id,
            receiver_id=target_id,
            item_name="Linh Thạch",
            so_luong=1,
            gia_lt=lt_thuc_te,
        )

        cap = get_quan_he_cap(qh["diem"])
        ts_viewer_dh = await get_tu_si(viewer_id)
        sender_dh = ts_viewer_dh["dao_hieu"] if ts_viewer_dh else inter.user.display_name
        await safe_followup(inter, 
            embed=e_ok(f"{E_LINH_THACH} Đã Tặng Linh Thạch!", (
                f"Bạn đã tặng {E_LINH_THACH} **{fmt(lt_thuc_te)} LT** cho "
                f"**{self.view_parent.user_target.display_name}**\n"
                f"❤️ Quan hệ: **{qh['diem']:+d}** điểm — *{cap['ten']}*\n"
                f"⏳ Còn có thể tặng hôm nay: **{con_lai_diem - diem_thuc_te}** điểm QH"
            )),
            ephemeral=True,
        )
        # DM người nhận
        await _dm_tang_qua(inter.client, target_id, sender_dh,
            f"{E_LINH_THACH} Linh Thạch", f"{fmt(lt_thuc_te)} LT",
            diem_thuc_te, qh["diem"])
        # Refresh view
        await self.view_parent._reload_view(inter)


# ══════════════════════════════════════════════════════
#  TẶNG QUÀ MODAL — Đan Dược
# ══════════════════════════════════════════════════════
class TangDanDuocModal(discord.ui.Modal, title="🔮 Tặng Đan Dược"):
    so_luong = discord.ui.TextInput(
        label="Số viên đan dược",
        placeholder="1 viên = 20 điểm QH",
        required=True,
        max_length=3,
    )

    def __init__(self, parent: "TangQuaView", dan_id: int):
        super().__init__()
        self.view_parent = parent
        self.dan_id = dan_id

    async def on_submit(self, inter: discord.Interaction):
        try:
            so = int(self.so_luong.value.strip())
        except ValueError:
            return await inter.response.send_message(
                embed=e_loi("❌ Lỗi", "Vui lòng nhập số hợp lệ!"), ephemeral=True)
        if so <= 0:
            return await inter.response.send_message(
                embed=e_loi("❌ Lỗi", "Số viên phải > 0!"), ephemeral=True)

        viewer_id = inter.user.id
        target_id = self.view_parent.ts_target["user_id"]
        dan       = DAN_DUOC[self.dan_id]

        # Kiểm tra kho đan của người tặng
        ts_viewer  = await get_tu_si(viewer_id)
        kho_dan    = ts_viewer.get("dan_duoc", {})
        co_trong_kho = kho_dan.get(str(self.dan_id), 0)
        if co_trong_kho < so:
            return await inter.response.send_message(
                embed=e_loi("❌ Không Đủ Đan Dược",
                    f"Bạn chỉ có **{co_trong_kho}** viên {E_DAN_DUOC} {dan['ten']}!"),
                ephemeral=True)

        # Kiểm tra giới hạn ngày
        da_tang_hom_nay = await get_tang_qua_hom_nay(viewer_id, target_id)
        con_lai_diem    = TANG_QUA_DIEM_MAX_NGAY - da_tang_hom_nay
        if con_lai_diem <= 0:
            return await inter.response.send_message(
                embed=e_warn("⏳ Đã Đạt Giới Hạn", "Bạn đã tặng đủ **100 điểm QH** hôm nay cho người này!"),
                ephemeral=True)

        # Tính số viên thực tế
        diem_toi_da  = (con_lai_diem // TANG_QUA_DAN_PER_DIEM)
        so_thuc_te   = min(so, diem_toi_da)
        diem_thuc_te = so_thuc_te * TANG_QUA_DAN_PER_DIEM

        if so_thuc_te <= 0:
            return await inter.response.send_message(
                embed=e_warn("⚠️ Đã Đạt Giới Hạn",
                    f"Bạn chỉ còn **{con_lai_diem}** điểm QH hôm nay, "
                    f"không đủ để tặng thêm đan dược ({TANG_QUA_DAN_PER_DIEM}đ/viên)!"),
                ephemeral=True)

        await inter.response.defer(ephemeral=True)
        # Thực hiện giao dịch
        kho_dan[str(self.dan_id)] = co_trong_kho - so_thuc_te
        await update_tu_si(viewer_id, dan_duoc=kho_dan)

        ts_target  = await get_tu_si(target_id)
        kho_target = ts_target.get("dan_duoc", {})
        kho_target[str(self.dan_id)] = kho_target.get(str(self.dan_id), 0) + so_thuc_te
        await update_tu_si(target_id, dan_duoc=kho_target)

        qh = await upsert_quan_he(viewer_id, target_id, diem_delta=diem_thuc_te)
        await add_tang_qua_log(viewer_id, target_id, diem_thuc_te)
        await log_giao_dich(
            "tang_dan",
            sender_id=viewer_id,
            receiver_id=target_id,
            item_name=dan["ten"],
            so_luong=so_thuc_te,
            gia_lt=0,
        )

        cap = get_quan_he_cap(qh["diem"])
        ts_viewer_dh2 = await get_tu_si(viewer_id)
        sender_dh2 = ts_viewer_dh2["dao_hieu"] if ts_viewer_dh2 else inter.user.display_name
        await safe_followup(inter, 
            embed=e_ok(f"{E_DAN_DUOC} Đã Tặng Đan Dược!", (
                f"Bạn đã tặng **{so_thuc_te}** viên {E_DAN_DUOC} **{dan['ten']}** cho "
                f"**{self.view_parent.user_target.display_name}**\n"
                f"❤️ Quan hệ: **{qh['diem']:+d}** điểm — *{cap['ten']}*\n"
                f"⏳ Còn có thể tặng hôm nay: **{con_lai_diem - diem_thuc_te}** điểm QH"
            )),
            ephemeral=True,
        )
        # DM người nhận
        await _dm_tang_qua(inter.client, target_id, sender_dh2,
            f"{E_DAN_DUOC} Đan Dược", f"{so_thuc_te} viên {dan['ten']}",
            diem_thuc_te, qh["diem"])
        await self.view_parent._reload_view(inter)


# ══════════════════════════════════════════════════════
#  CHỌN ĐAN DỰC SELECT
# ══════════════════════════════════════════════════════
class ChonDanSelect(discord.ui.Select):
    def __init__(self, parent: "TangQuaView", ts_viewer: dict):
        kho = ts_viewer.get("dan_duoc", {})
        options = []
        for d in DAN_DUOC:
            so = kho.get(str(d["id"]), 0)
            if so > 0:
                options.append(discord.SelectOption(
                    label=f"{d['ten']} (x{so})",
                    value=str(d["id"]),
                    emoji=_parse_emoji(d["emoji"]),
                    description=f"1 viên = {TANG_QUA_DAN_PER_DIEM} điểm QH",
                ))
        if not options:
            options = [discord.SelectOption(
                label="Kho đan trống",
                value="empty",
                description="Bạn không có đan dược nào để tặng",
            )]
        super().__init__(
            placeholder="Chọn loại đan dược muốn tặng...",
            options=options,
            row=2,
        )
        self.view_parent = parent  # ← đổi từ self.parent → self.view_parent

    async def callback(self, inter: discord.Interaction):
        if self.values[0] == "empty":
            return await inter.response.send_message(
                embed=e_warn(f"{E_DAN_DUOC} Kho Trống", "Bạn không có đan dược nào để tặng!"),
                ephemeral=True)
        dan_id = int(self.values[0])
        await inter.response.send_modal(TangDanDuocModal(self.view_parent, dan_id))


# ══════════════════════════════════════════════════════
#  TẶNG QUÀ VIEW
# ══════════════════════════════════════════════════════
class TangQuaView(discord.ui.View):
    def __init__(
        self,
        parent_view,
        ts_viewer: dict,
        ts_target: dict,
        user_viewer: discord.User,
        user_target: discord.User,
        qh: dict | None,
    ):
        super().__init__(timeout=120)
        self.parent_view = parent_view
        self.ts_viewer   = ts_viewer
        self.ts_target   = ts_target
        self.user_viewer = user_viewer
        self.user_target = user_target
        self.qh          = qh
        self._message: discord.Message | None = None
        self._build()

    def _build(self):
        self.clear_items()
        # Row 0: Tặng linh thạch
        btn_lt = discord.ui.Button(
            label="Tặng Linh Thạch",
            emoji=_parse_emoji(E_LINH_THACH),
            style=discord.ButtonStyle.primary,
            row=0,
        )
        btn_lt.callback = self._cb_tang_lt
        self.add_item(btn_lt)

        # Row 0: Kết giao (nếu đủ điểm)
        diem = self.qh["diem"] if self.qh else 0
        cap  = get_quan_he_cap(diem)
        if cap.get("ket_giao"):
            btn_kg = discord.ui.Button(
                label="💞 Kết Giao",
                style=discord.ButtonStyle.success,
                row=0,
            )
            btn_kg.callback = self._cb_ket_giao
            self.add_item(btn_kg)

        # Row 1: Back
        btn_back = discord.ui.Button(
            label="← Quay Lại",
            style=discord.ButtonStyle.secondary,
            row=1,
        )
        btn_back.callback = self._cb_back
        self.add_item(btn_back)

        # Row 2: Chọn đan dược
        self.add_item(ChonDanSelect(self, self.ts_viewer))

    async def _reload_view(self, inter: discord.Interaction):
        """Reload QH và cập nhật embed sau khi tặng."""
        qh_new = await get_quan_he(self.user_viewer.id, self.user_target.id)
        from utils.database import get_tu_si as _get
        ts_viewer_new = await _get(self.user_viewer.id) or self.ts_viewer
        embed = _embed_quan_he(
            ts_viewer_new, self.ts_target,
            self.user_viewer, self.user_target,
            qh_new,
        )
        # Tạo view mới hoàn toàn để tránh interaction failed
        new_view = TangQuaView(
            self.parent_view, ts_viewer_new, self.ts_target,
            self.user_viewer, self.user_target, qh_new,
        )
        new_view._message = self._message
        self.stop()
        if self._message:
            try:
                await self._message.edit(embed=embed, view=new_view)
                return
            except Exception:
                log.exception("Lỗi quan_he")
        try:
            await inter.edit_original_response(embed=embed, view=new_view)
        except Exception:
            log.exception("Lỗi quan_he")

    async def _cb_tang_lt(self, inter: discord.Interaction):
        if inter.user.id != self.user_viewer.id:
            return await inter.response.send_message("❌", ephemeral=True)
        await inter.response.send_modal(TangLinhThachModal(self))

    async def _cb_ket_giao(self, inter: discord.Interaction):
        if inter.user.id != self.user_viewer.id:
            return await inter.response.send_message("❌", ephemeral=True)
        diem = self.qh["diem"] if self.qh else 0
        view = KetGiaoView(self, self.user_viewer, self.user_target, diem, self.qh)
        embed = discord.Embed(
            title="💞 Kết Giao",
            description=f"Chọn loại kết giao với **{self.user_target.display_name}**",
            color=0xE91E8C,
        )
        await inter.response.send_message(embed=embed, view=view, ephemeral=True)

    async def _cb_back(self, inter: discord.Interaction):
        if inter.user.id != self.user_viewer.id:
            return await _back_to_hoso(inter, self.parent_view)
        try:
            await inter.response.defer()
        except Exception:
            log.exception("Lỗi quan_he")
        try:
            await inter.delete_original_response()
        except Exception:
            log.exception("Lỗi quan_he")


# ══════════════════════════════════════════════════════
#  KẾT GIAO VIEW
# ══════════════════════════════════════════════════════
class KetGiaoView(discord.ui.View):
    def __init__(
        self,
        parent: TangQuaView,
        user_viewer: discord.User,
        user_target: discord.User,
        diem: int,
        qh: dict | None,
    ):
        super().__init__(timeout=60)
        self.view_parent = parent
        self.user_viewer = user_viewer
        self.user_target = user_target
        self.diem        = diem
        self.qh          = qh
        self._build()

    def _build(self):
        self.clear_items()
        cap = get_quan_he_cap(self.diem)
        loai_hien = self.qh["loai"] if self.qh else ""

        for loai_key in cap.get("ket_giao", []):
            if loai_key not in QUAN_HE_LOAI:
                continue
            kl  = QUAN_HE_LOAI[loai_key]
            btn = discord.ui.Button(
                label=f"{kl['emoji']} {kl['ten']}",
                style=discord.ButtonStyle.success if loai_hien != loai_key
                      else discord.ButtonStyle.primary,
                disabled=(loai_hien == loai_key),
            )
            btn.callback = self._make_cb(loai_key)
            self.add_item(btn)

        if loai_hien:
            btn_huy = discord.ui.Button(
                label="💔 Hủy Kết Giao",
                style=discord.ButtonStyle.danger,
            )
            btn_huy.callback = self._cb_huy
            self.add_item(btn_huy)

    def _make_cb(self, loai_key: str):
        async def _cb(inter: discord.Interaction):
            if inter.user.id != self.user_viewer.id:
                return await inter.response.send_message("❌", ephemeral=True)
            await set_quan_he_loai(self.user_viewer.id, self.user_target.id, loai_key)
            kl = QUAN_HE_LOAI[loai_key]
            await inter.response.edit_message(
                embed=e_ok("💞 Đã Kết Giao!", (
                    f"Bạn và **{self.user_target.display_name}** "
                    f"đã kết giao: {kl['emoji']} **{kl['ten']}**"
                )),
                view=None,
            )
            await self.view_parent._reload_view(inter)
        return _cb

    async def _cb_huy(self, inter: discord.Interaction):
        if inter.user.id != self.user_viewer.id:
            return await inter.response.send_message("❌", ephemeral=True)
        await set_quan_he_loai(self.user_viewer.id, self.user_target.id, "")
        await inter.response.edit_message(
            embed=e_ok("💔 Đã Hủy Kết Giao", "Quan hệ đã được đặt lại về trạng thái bình thường."),
            view=None,
        )
        await self.view_parent._reload_view(inter)
