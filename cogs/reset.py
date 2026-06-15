"""
COG: Tự Reset Nhân Vật — /reset (tối đa 3 lần)
Reset count lưu trong bảng reset_log riêng, không bị mất khi xóa nhân vật.
"""
from __future__ import annotations

import discord
from discord import app_commands
from discord.ext import commands
from utils.database import get_tu_si, delete_tu_si, get_reset_count, increment_reset_count
from utils.embeds import e_loi, e_ok
from utils.embeds import safe_followup

MAX_RESET = 3


class ConfirmResetView(discord.ui.View):
    def __init__(self, user_id: int, dao_hieu: str):
        super().__init__(timeout=30)
        self.user_id  = user_id
        self.dao_hieu = dao_hieu

    @discord.ui.button(label="✅ Xác nhận Reset", style=discord.ButtonStyle.danger)
    async def confirm(self, inter: discord.Interaction, button: discord.ui.Button):
        if inter.user.id != self.user_id:
            return await inter.response.send_message(
                embed=e_loi("Không Hợp Lệ", "Đây không phải lệnh của bạn!"), ephemeral=True)

        await inter.response.defer(ephemeral=True)

        count = await get_reset_count(self.user_id)
        if count >= MAX_RESET:
            self.stop()
            return await safe_followup(inter, 
                embed=e_loi("Hết Lượt", f"Đã dùng hết **{MAX_RESET}/{MAX_RESET}** lượt reset!"),
                ephemeral=True)

        # Tăng count TRƯỚC khi xóa
        new_count = await increment_reset_count(self.user_id)
        await delete_tu_si(self.user_id)

        con_lai = MAX_RESET - new_count
        for item in self.children:
            item.disabled = True
        self.stop()

        embed = discord.Embed(
            title="💀 NHÂN VẬT ĐÃ XÓA",
            description=(
                f"**{self.dao_hieu}** đã bị xóa hoàn toàn.\n\n"
                f"Dùng **/hoso** để tạo nhân vật mới!\n\n"
                f"🔄 Đã dùng: **{new_count}/{MAX_RESET}** lượt reset\n"
                + ("⚠️ Đây sẽ là lần trùng sinh cuối cùng, đạo hữu đừng nên quá cố gắng..."
                   if con_lai == 0 else f"Còn lại: **{con_lai}** lượt")
            ),
            color=0xED4245)
        embed.set_footer(text="Chúc may mắn trên con đường tu tiên mới!")
        await safe_followup(inter, embed=embed, ephemeral=True)

    @discord.ui.button(label="❌ Hủy", style=discord.ButtonStyle.secondary)
    async def cancel(self, inter: discord.Interaction, button: discord.ui.Button):
        if inter.user.id != self.user_id:
            return await inter.response.send_message(
                embed=e_loi("Không Hợp Lệ", "Đây không phải lệnh của bạn!"), ephemeral=True)
        for item in self.children:
            item.disabled = True
        self.stop()
        await inter.response.edit_message(
            embed=e_ok("Đã Hủy", "Nhân vật của bạn vẫn an toàn! 😌"), view=self)


class ResetCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="reset", description="Xóa toàn bộ nhân vật và bắt đầu lại (tối đa 3 lần)")
    async def reset(self, inter: discord.Interaction):
        await inter.response.defer(ephemeral=True)

        ts = await get_tu_si(inter.user.id)
        if not ts:
            return await safe_followup(inter, 
                embed=e_loi("Chưa Tu Tiên", "Dùng **/hoso** để đăng ký trước!"), ephemeral=True)

        count   = await get_reset_count(inter.user.id)
        con_lai = MAX_RESET - count

        if count >= MAX_RESET:
            return await safe_followup(inter, 
                embed=e_loi("Hết Lượt Reset",
                    f"Đã dùng hết **{MAX_RESET}/{MAX_RESET}** lượt.\nKhông thể reset thêm!"),
                ephemeral=True)

        dao_hieu = ts.get("dao_hieu", "Vô Danh")
        embed = discord.Embed(
            title="⚠️ XÁC NHẬN XÓA NHÂN VẬT",
            description=(
                f"Bạn sắp xóa toàn bộ data của **{dao_hieu}**.\n"
                f"Hành động này **không thể hoàn tác**!\n\n"
                f"🔄 Lượt reset: **{count+1}/{MAX_RESET}**\n"
                f"Sau khi reset còn lại: **{con_lai-1}** lượt\n\n"
                + ("⚠️ **Đây là lần trùng sinh cuối cùng!**" if con_lai == 1 else "")
            ),
            color=0xFEE75C)
        embed.set_author(name=inter.user.display_name, icon_url=inter.user.display_avatar.url)
        embed.set_footer(text="Xác nhận trong vòng 30 giây")
        await safe_followup(inter, embed=embed, view=ConfirmResetView(inter.user.id, dao_hieu), ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(ResetCog(bot))
