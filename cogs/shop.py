"""
COG: Shop / Promo Code
Commands: /gencode, /redeem
Button: Hiển thị QR + giá 3 gói
"""
from __future__ import annotations

import logging
import random
import string
from typing import Any

import discord
from discord import app_commands
from discord.ext import commands

from utils.config import (
    OWNER_IDS,
    DOTPHA_TC_NGUYEN_LIEU,
    LINH_QUA,
    PHAP_BAO,
    SHOP_PACKAGES,
    SHOP_QR_1,
    SHOP_QR_2,
    SHOP_CONTACT_ID,
)
from utils.database import (
    create_promo_code,
    get_tu_si,
    redeem_promo_code,
    update_tu_si,
)
from utils.embeds import e_loi, e_ok, owner_only_check, safe_followup

log = logging.getLogger("shop")


# ── Helpers ──────────────────────────────────────────────────────────────────

def _random_code(length: int = 8) -> str:
    """Tạo code ngẫu nhiên: chữ hoa + số."""
    alphabet = string.ascii_uppercase + string.digits
    return "".join(random.choices(alphabet, k=length))


def _fulfill_package(ts: dict[str, Any], goi: str) -> tuple[dict[str, Any], str]:
    """
    Thêm phần thưởng vào dict tu_si, trả về (ts_moi, mô tả).
    ts phải là copy trước khi gọi.
    """
    desc_lines: list[str] = []

    if goi == "dot_pha_tc":
        kho = ts.get("dotpha_tc_nl", {})
        if not isinstance(kho, dict):
            kho = {}
        for nl in DOTPHA_TC_NGUYEN_LIEU:
            kho[nl["id"]] = kho.get(nl["id"], 0) + 1
        ts["dotpha_tc_nl"] = kho
        desc_lines = [f"{nl['emoji']} {nl['ten']} ×1" for nl in DOTPHA_TC_NGUYEN_LIEU]

    elif goi == "ngu_hanh_qua":
        lq = ts.get("linh_qua", {})
        if not isinstance(lq, dict):
            lq = {}
        co_ban = [q for q in LINH_QUA if q.get("loai") == "co_ban"]
        for q in co_ban:
            lq[q["id"]] = lq.get(q["id"], 0) + 20
        ts["linh_qua"] = lq
        desc_lines = [f"{q['emoji']} {q['ten']} ×{lq.get(q['id'], 0)}" for q in co_ban]

    elif goi == "phap_bao":
        pb_ids = ts.get("phap_bao", [])
        if not isinstance(pb_ids, list):
            pb_ids = []
        chosen_id = random.randint(0, len(PHAP_BAO) - 1)
        pb_ids.append(chosen_id)
        ts["phap_bao"] = pb_ids
        pb = PHAP_BAO[chosen_id]
        desc_lines = [f"{pb['emoji']} **{pb['ten']}** (Cảnh giới: {pb.get('canh_gioi', '?')})"]

    return ts, "\n".join(desc_lines)


# ── View (Button) ────────────────────────────────────────────────────────────

class ShopView(discord.ui.View):
    """Persistent view hiển thị thông tin shop + QR placeholder."""

    def __init__(self) -> None:
        super().__init__(timeout=None)

    @discord.ui.button(
        label="🛒 Mua Gói",
        style=discord.ButtonStyle.primary,
        custom_id="shop_buy_button",
    )
    async def shop_button(
        self, interaction: discord.Interaction, button: discord.ui.Button[Any]
    ) -> None:
        contact = f"<@{SHOP_CONTACT_ID}>"
        embed = discord.Embed(
            title="🛒 Thiên Đế Shop",
            description=(
                "**HƯỚNG DẪN MUA:**\n"
                "1️⃣ Chọn gói bên dưới\n"
                "2️⃣ Chuyển khoản đúng số tiền vào 1 trong 2 QR\n"
                "3️⃣ Gửi bill xác nhận cho " + contact + "\n"
                "4️⃣ Nhận code → dùng `/redeem <CODE>` để nhận thưởng!"
            ),
            color=0x5865F2,
        )

        for _pkg_id, pkg in SHOP_PACKAGES.items():
            gia_fmt = f"{pkg['gia']:,}".replace(",", ".")
            embed.add_field(
                name=f"{pkg['emoji']} {pkg['ten']}",
                value=f"{pkg['mo_ta']}\n💰 Giá: **{gia_fmt} VNĐ**",
                inline=False,
            )

        embed.set_image(url="attachment://qr1.jpg")
        embed.set_thumbnail(url="attachment://qr2.jpg")
        embed.set_footer(text=f"Gửi bill cho {contact} để nhận code!")

        files: list[discord.File] = []
        if SHOP_QR_1:
            files.append(discord.File(SHOP_QR_1, filename="qr1.jpg"))
        if SHOP_QR_2:
            files.append(discord.File(SHOP_QR_2, filename="qr2.jpg"))
        await interaction.response.send_message(embed=embed, files=files, ephemeral=True)


# ── Cog ──────────────────────────────────────────────────────────────────────

class Shop(commands.Cog):
    """Shop & Promo Code system."""

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self) -> None:
        self.bot.add_view(ShopView())
        log.info("ShopView registered (persistent)")

    # ── /gencode ─────────────────────────────────────────────────────────
    @app_commands.command(name="gencode", description="[Owner] Tạo promo code cho gói")
    @app_commands.describe(
        goi="Loại gói: dot_pha_tc / ngu_hanh_qua / phap_bao",
        code="Code tuỳ ý (để trống = random)",
        so_luong="Số code cần tạo (1-20)",
    )
    @app_commands.choices(
        goi=[
            app_commands.Choice(name="💎 Đột Phá Thân Cấp", value="dot_pha_tc"),
            app_commands.Choice(name="🍎 Ngũ Hành Linh Quả", value="ngu_hanh_qua"),
            app_commands.Choice(name="⚔️ Pháp Bảo Ngẫu Nhiên", value="phap_bao"),
        ]
    )
    @owner_only_check(OWNER_IDS)
    async def gencode(
        self,
        interaction: discord.Interaction,
        goi: app_commands.Choice[str],
        so_luong: app_commands.Range[int, 1, 20] = 1,
        code: str | None = None,
    ) -> None:
        await interaction.response.defer(ephemeral=True)

        pkg = SHOP_PACKAGES.get(goi.value)
        if not pkg:
            return await safe_followup(interaction, embed=e_loi("Lỗi", "Gói không hợp lệ!"))

        created: list[str] = []
        failed = 0
        for _ in range(so_luong):
            c = code if (code and so_luong == 1) else _random_code()
            ok = await create_promo_code(c, goi.value, interaction.user.id)
            if ok:
                created.append(c)
            else:
                failed += 1

        if not created:
            return await safe_followup(
                interaction, embed=e_loi("Lỗi", "Không tạo được code nào (có thể bị trùng)!")
            )

        lines = "\n".join(f"`{c}`" for c in created)
        desc = f"**Gói:** {pkg['emoji']} {pkg['ten']}\n**Số lượng:** {len(created)}\n\n{lines}"
        if failed:
            desc += f"\n\n⚠️ {failed} code bị trùng, đã bỏ qua."

        await safe_followup(interaction, embed=e_ok("Tạo Code Thành Công", desc))

    # ── /redeem ──────────────────────────────────────────────────────────
    @app_commands.command(name="redeem", description="Nhập promo code để nhận phần thưởng")
    @app_commands.describe(code="Mã promo code")
    async def redeem(
        self, interaction: discord.Interaction, code: str
    ) -> None:
        await interaction.response.defer(ephemeral=True)

        code = code.strip().upper()
        result = await redeem_promo_code(code, interaction.user.id)
        if not result:
            return await safe_followup(
                interaction,
                embed=e_loi("Code Không Hợp Lệ", "Code không tồn tại hoặc đã được sử dụng!"),
            )

        goi: str = result["goi"]
        pkg = SHOP_PACKAGES.get(goi)
        if not pkg:
            return await safe_followup(interaction, embed=e_loi("Lỗi", f"Gói `{goi}` không tồn tại!"))

        ts = await get_tu_si(interaction.user.id)
        if not ts:
            return await safe_followup(
                interaction,
                embed=e_loi("Chưa Có Hồ Sơ", "Bạn cần tạo hồ sơ trước khi redeem code!"),
            )

        ts_copy = ts.copy()
        ts_new, desc = _fulfill_package(ts_copy, goi)
        await update_tu_si(interaction.user.id, **{
            k: v for k, v in ts_new.items() if k in ("dotpha_tc_nl", "linh_qua", "phap_bao")
        })

        gia_fmt = f"{pkg['gia']:,}".replace(",", ".")
        embed = discord.Embed(
            title="🎉 Redeem Thành Công!",
            description=(
                f"**Code:** `{code}`\n"
                f"**Gói:** {pkg['emoji']} {pkg['ten']}\n"
                f"**Giá trị:** {gia_fmt} VNĐ\n\n"
                f"**Phần thưởng:**\n{desc}"
            ),
            color=0x57F287,
        )
        embed.set_thumbnail(url=interaction.user.display_avatar.url)
        embed.set_footer(text="Chúc mừng tu sĩ! 🎊")
        await safe_followup(interaction, embed=embed)

    # ── /shop (hiển thị button) ──────────────────────────────────────────
    @app_commands.command(name="shop", description="Xem cửa hàng và mua gói")
    async def shop(self, interaction: discord.Interaction) -> None:
        contact = f"<@{SHOP_CONTACT_ID}>"
        embed = discord.Embed(
            title="🛒 Thiên Đế Shop",
            description=(
                "**HƯỚNG DẪN MUA:**\n"
                "1️⃣ Nhấn nút **🛒 Mua Gói** bên dưới\n"
                "2️⃣ Chuyển khoản đúng số tiền vào 1 trong 2 QR\n"
                "3️⃣ Gửi bill xác nhận cho " + contact + "\n"
                "4️⃣ Nhận code → dùng `/redeem <CODE>` để nhận thưởng!"
            ),
            color=0x5865F2,
        )
        await interaction.response.send_message(embed=embed, view=ShopView())


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Shop(bot))
