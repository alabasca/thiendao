from __future__ import annotations
from typing import Any

from cogs.views._common import *
from utils.bot_emojis import E_SINH_LUC, E_CONG_KICH, E_PHONG_NGU, E_HOI_TAM, E_HO_TAM, E_BAO_KICH, E_KHANG_BAO, E_TU_VI, E_LINH_THACH
import re as _re
import logging
from typing import TYPE_CHECKING
log = logging.getLogger("hoso")

if TYPE_CHECKING:
    from cogs.hoso import HoSoView

# HoSoView nằm trong cogs.hoso — import lazy trong hàm để tránh circular import
def _get_hoso_view():
    from cogs.hoso import HoSoView
    return HoSoView


class _DangKyTriggerView(discord.ui.View):
    """Gửi ephemeral button để mở DangKyModal từ interaction mới.
    Dùng khi /hoso đã defer() trước → không thể send_modal trực tiếp nữa."""

    def __init__(self, user_id: int):
        super().__init__(timeout=120)
        self.user_id = user_id

    @discord.ui.button(label="✦ Nhập Môn Tu Tiên", style=discord.ButtonStyle.primary)
    async def btn_dang_ky(self, inter: discord.Interaction, button: discord.ui.Button):
        if inter.user.id != self.user_id:
            return await inter.response.send_message("❌ Không phải lệnh của bạn!", ephemeral=True)
        self.stop()
        await inter.response.send_modal(DangKyModal())


class DangKyModal(discord.ui.Modal, title="✦ Nhập Môn Tu Tiên ✦"):
    dao_hieu = discord.ui.TextInput(
        label="Đạo Hiệu", placeholder="Nhập đạo hiệu của bạn...",
        min_length=1, max_length=20)

    async def on_submit(self, inter: discord.Interaction):
        # Double-check tuổi tài khoản (phòng bypass modal)
        import datetime as _dt
        acc_age_days = (_dt.datetime.now(_dt.timezone.utc) - inter.user.created_at).days
        if acc_age_days < 30:
            return await inter.response.send_message(
                f"❌ Tài khoản chỉ mới **{acc_age_days} ngày** — cần tối thiểu **30 ngày**!",
                ephemeral=True)
        try:
            await inter.response.defer(thinking=True)
        except Exception:
            log.exception("Lỗi profile")
        # Random thể chất + linh căn khởi đầu (1-5 căn cơ bản)
        from utils.config import random_linh_can_khoi_dau
        tc_id   = random_the_chat()
        tc      = THE_CHAT_BY_ID.get(tc_id, THE_CHAT[-1])
        lc_ids  = random_linh_can_khoi_dau()   # list 1–5 căn
        lc_diem = {lc_id: 0 for lc_id in lc_ids}

        ts = await create_tu_si(inter.user.id, self.dao_hieu.value, 0)
        from utils.database import update_tu_si as _upd
        await _upd(inter.user.id,
            the_chat=tc_id,
            linh_can_so_huu=lc_ids,
            linh_can_diem=lc_diem,
            manh_linh_can={})
        ts["the_chat"]        = tc_id
        ts["linh_can_so_huu"] = lc_ids

        # Lấy thông tin căn đầu tiên để hiển thị chính (các căn khác hiển thị gọn)
        lc     = LINH_CAN_BY_ID.get(lc_ids[0]) if lc_ids else None

        embed = discord.Embed(
            title="🌟 NHẬP MÔN TU TIÊN!",
            description=f"**{self.dao_hieu.value}** chính thức bước vào đường tu tiên!",
            color=tc["mau"])
        embed.add_field(
            name=f"{tc['emoji']} Thể Chất Tu Luyện",
            value=f"**{tc['ten']}**\n*{tc['mo_ta']}*",
            inline=False)
        if lc:
            STAT_LABEL = {
                "at_flat":   f"{E_CONG_KICH} Tấn công",
                "df_flat":   f"{E_PHONG_NGU} Phòng ngự",
                "hp_flat":   f"{E_SINH_LUC} Sinh lực",
                "hoi_tam":   f"{E_HOI_TAM} Hội tâm",
                "ho_tam":    f"{E_HO_TAM} Hộ tâm",
                "bao_kich":  f"{E_BAO_KICH} Bạo kích",
                "khang_bao": f"{E_KHANG_BAO} Kháng bạo",
                "drop_rate": "🍀 Drop rate",
                "exp_pct":   f"{E_TU_VI} Tu vi nhận",
            }
            # Hiển thị từng linh căn
            for _lc_id in lc_ids:
                _lc = LINH_CAN_BY_ID.get(_lc_id)
                if not _lc: continue
                p = _lc.get("passive", {})
                passive_lines = []
                for k, v in p.items():
                    label = STAT_LABEL.get(k, k)
                    if "pct" in k or k in ("bao_kich", "khang_bao", "drop_rate", "exp_pct"):
                        passive_lines.append(f"{label}: **+{v}%**")
                    elif k in ("hoi_tam", "ho_tam"):
                        passive_lines.append(f"{label}: **+{v}đ**")
                    else:
                        passive_lines.append(f"{label}: **+{v}**")
                dot_pha_b = _lc.get("dot_pha_buff", {})
                dp_lines = []
                for k, v in dot_pha_b.items():
                    label = STAT_LABEL.get(k, k)
                    if "pct" in k or k in ("bao_kich", "khang_bao"):
                        dp_lines.append(f"{label}: **+{v}%** / lần đột phá")
                    else:
                        dp_lines.append(f"{label}: **+{v}** / lần đột phá")
                # Hiển thị buff lớp 2 đã tích lũy thực tế
                lop2_all = ts.get("linh_can_lop2", {}) or {}
                if isinstance(lop2_all, str):
                    import json as _jlp
                    try: lop2_all = _jlp.loads(lop2_all) if lop2_all else {}
                    except Exception: lop2_all = {}
                lop2_lines = []
                for k, v in lop2_all.items():
                    if v:
                        label = STAT_LABEL.get(k, k)
                        if "pct" in k or k in ("bao_kich", "khang_bao"):
                            lop2_lines.append(f"{label}: **+{round(v, 2)}%** ✅")
                        else:
                            lop2_lines.append(f"{label}: **+{int(v)}** ✅")
                lc_val = (
                    f"**{_lc['ten']}**\n"
                    f"*{_lc['chuc_mung']}*\n\n"
                    f"**Passive thường trực:**\n" + "\n".join(passive_lines)
                    + (("\n\n**Buff đột phá / lần:**\n" + "\n".join(dp_lines)) if dp_lines else "")
                    + (("\n\n**Buff lớp 2 đã tích lũy:**\n" + "\n".join(lop2_lines)) if lop2_lines else "")
                    + (("\n\n📊 **Buff cộng vào chỉ số cơ bản** (ATK/DEF/HP mỗi lần đột phá):\n"
                        + "\n".join(
                            f"{'ATK' if k=='at_pct' else 'DEF' if k=='def_pct' else 'HP'} **+{v}%**"
                            for k, v in dot_pha_b.items()
                            if k in ("at_pct", "def_pct", "hp_pct")
                        )) if any(k in dot_pha_b for k in ("at_pct","def_pct","hp_pct")) else "")
                )
                if len(lc_val) > 1020: lc_val = lc_val[:1017] + "..."
                field_name = f"{_lc['emoji']} Linh Căn Khởi Đầu"
                if len(lc_ids) > 1:
                    field_name += f" ({lc_ids.index(_lc_id)+1}/{len(lc_ids)})"
                embed.add_field(name=field_name, value=lc_val, inline=False)

        # Thể chất buff
        tc_buff = tc.get("buff", {})
        TC_LABEL = {
            "at_pct":           f"{E_CONG_KICH} Tấn công",
            "def_pct":          f"{E_PHONG_NGU} Phòng ngự",
            "hp_pct":           f"{E_SINH_LUC} Sinh lực",
            "exp_m":            f"{E_TU_VI} Tu vi",
            "lt_m":             f"{E_LINH_THACH} Linh thạch",
            "drop_rate":        "🍀 Drop rate",
            "hoi_tam":          f"{E_HOI_TAM} Hội tâm",
            "bao_kich":         f"{E_BAO_KICH} Bạo kích",
            "khang_bao":        f"{E_KHANG_BAO} Kháng bạo",
            "ho_tam":           f"{E_HO_TAM} Hộ tâm",
            "cd_tu_luyen_pct":  "⏱️ CD tu luyện",
        }
        tc_lines = []
        for k, v in tc_buff.items():
            label = TC_LABEL.get(k, k)
            if k in ("exp_m", "lt_m"):
                tc_lines.append(f"{label}: **×{v}**")
            elif "pct" in k or k in ("bao_kich", "khang_bao", "drop_rate"):
                tc_lines.append(f"{label}: **{'+' if v > 0 else ''}{v}%**")
            elif k in ("hoi_tam", "ho_tam"):
                tc_lines.append(f"{label}: **+{v}đ**")
        if tc_lines:
            embed.add_field(
                name=f"{tc['emoji']} Buff Thể Chất",
                value="\n".join(tc_lines),
                inline=False)

        embed.add_field(name="🌱 Cảnh Giới", value="**Sơ Kỳ Luyện Khí**", inline=False)
        embed.add_field(name=f"{E_LINH_THACH} Quà Khởi Đầu", value="**20,000** linh thạch — cơ duyên ban đầu từ Thiên Đạo!", inline=False)
        embed.add_field(
            name="📌 Lưu ý",
            value=(
                "• Linh căn **passive** luôn active, không cần kích hoạt\n"
                "• Buff đột phá **cộng dồn** mỗi lần đột phá đại cảnh\n"
                "• Có thể kiếm thêm linh căn qua **mảnh drop** từ bí cảnh & boss"
            ),
            inline=False)
        embed.set_footer(text=tc["chuc_mung"])
        await safe_followup(inter, embed=embed)

        ts_fresh = await get_tu_si(inter.user.id) or ts
        view = _get_hoso_view()(ts_fresh, inter.user, inter.user.id)
        msg = await safe_followup(inter, embed=_embed_hoso(ts_fresh, inter.user), view=view)
        view._message = msg



# ══════════════════════════════════════════════════════════════
#  CHỈNH SỬA HỒ SƠ MODAL

class ChinhSuaModal(discord.ui.Modal, title="✏️ Chỉnh Sửa Hồ Sơ"):
    dao_hieu_new = discord.ui.TextInput(
        label="Đạo Hiệu (đổi tên tốn 10,000 LT)",
        placeholder="Để trống nếu không muốn đổi",
        required=False,
        max_length=30)
    gioi_tinh = discord.ui.TextInput(
        label="Giới Tính",
        placeholder="Nam / Nữ / Khác",
        required=False,
        max_length=10)
    tuoi = discord.ui.TextInput(
        label="Tuổi",
        placeholder="Nhập số tuổi (vd: 18)",
        required=False,
        max_length=3)
    so_thich = discord.ui.TextInput(
        label="Sở Thích",
        placeholder="Nhập sở thích của bạn...",
        required=False,
        max_length=100,
        style=discord.TextStyle.paragraph)

    def __init__(self, parent: "HoSoView", ts: dict[str, Any]):
        super().__init__()
        self.parent = parent
        self.ts_cu  = ts
        if ts.get("gioi_tinh"):
            self.gioi_tinh.default = ts["gioi_tinh"]
        if ts.get("tuoi"):
            self.tuoi.default = str(ts["tuoi"])
        if ts.get("so_thich"):
            self.so_thich.default = ts["so_thich"]

    async def on_submit(self, inter: discord.Interaction):
        DOI_TEN_GIA = 10000
        # Validate tuổi
        tuoi_val = 0
        if self.tuoi.value.strip():
            try:
                tuoi_val = int(self.tuoi.value.strip())
                if tuoi_val < 0 or tuoi_val > 999:
                    return await inter.response.send_message(
                        "❌ Tuổi không hợp lệ (0–999)!", ephemeral=True)
            except ValueError:
                return await inter.response.send_message(
                    "❌ Tuổi phải là số!", ephemeral=True)

        gioi_tinh_val = self.gioi_tinh.value.strip()
        so_thich_val  = self.so_thich.value.strip()
        dao_hieu_val  = self.dao_hieu_new.value.strip()

        await inter.response.defer(ephemeral=True)
        ts = await get_tu_si(inter.user.id)
        update_kwargs = dict(gioi_tinh=gioi_tinh_val, tuoi=tuoi_val, so_thich=so_thich_val)
        ten_tag = ""

        if dao_hieu_val:
            if dao_hieu_val == self.ts_cu.get("dao_hieu", ""):
                return await safe_followup(inter, 
                    "❌ Đạo hiệu mới phải khác đạo hiệu cũ!", ephemeral=True)
            if ts["linh_thach"] < DOI_TEN_GIA:
                return await safe_followup(inter, 
                    f"❌ Không đủ Linh Thạch! Cần **{DOI_TEN_GIA:,}** LT để đổi tên.", ephemeral=True)
            update_kwargs["dao_hieu"]    = dao_hieu_val
            update_kwargs["linh_thach"] = ts["linh_thach"] - DOI_TEN_GIA
            ten_tag = f"\n**Đạo Hiệu:** {self.ts_cu.get('dao_hieu','')} → **{dao_hieu_val}** (-{DOI_TEN_GIA:,} LT)"

        await update_tu_si(inter.user.id, **update_kwargs)

        await safe_followup(inter, 
            embed=e_ok("✅ Đã Cập Nhật Hồ Sơ!", (
                    (ten_tag + "\n" if ten_tag else "")
                    + f"**Giới tính:** {gioi_tinh_val or '*(không đổi)*'}\n"
                    + f"**Tuổi:** {tuoi_val if tuoi_val else '*(không đổi)*'}\n"
                    + f"**Sở thích:** {so_thich_val or '*(không đổi)*'}"
                )),
            ephemeral=True)

        # Cập nhật lại embed hồ sơ gốc (message gốc của HoSoView)
        await self.parent._reload()
        self.parent._rebuild()
        try:
            msg = self.parent._message
            if msg:
                await msg.edit(embed=self.parent._current_embed(), view=self.parent, attachments=[])
        except Exception as e:
            log.warning(f"ChinhSuaModal on_submit message edit failed: {e}")


# ══════════════════════════════════════════════════════════════
#  COG
# ══════════════════════════════════════════════════════════════
