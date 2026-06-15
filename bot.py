"""
╔══════════════════════════════════════════════════════╗
║     QUỶ CỐC BÁT HOANG — TU TIÊN BOT v3.0           ║
║     Multi-Cog Architecture                          ║
╚══════════════════════════════════════════════════════╝

Cài đặt:
    pip install -r requirements.txt

Chạy:
    BOT_TOKEN=your_token python bot.py
"""

import discord
from discord.ext import commands
import asyncio, os, sys, logging, time
from logging.handlers import RotatingFileHandler
from utils.config import TOKEN
from utils.database import init_db, close_db
from utils.emoji_manager import setup_emojis
from utils.embeds import safe_followup

# ══════════════════════════════════════════════════════
#  LOGGING SETUP
# ══════════════════════════════════════════════════════
os.makedirs("logs", exist_ok=True)

# Format chung
fmt = logging.Formatter(
    "[%(asctime)s] [%(levelname)-8s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)

# Handler: file xoay vòng 5MB × 5 bản
file_handler = RotatingFileHandler(
    "logs/bot.log", maxBytes=5 * 1024 * 1024, backupCount=5, encoding="utf-8"
)
file_handler.setFormatter(fmt)
file_handler.setLevel(logging.INFO)

# Handler: console chỉ WARNING+
console_handler = logging.StreamHandler(sys.stdout)
console_handler.setFormatter(fmt)
console_handler.setLevel(logging.WARNING)

# Root logger
root_logger = logging.getLogger()
root_logger.setLevel(logging.INFO)
root_logger.addHandler(file_handler)
root_logger.addHandler(console_handler)

# Tắt noise từ thư viện bên ngoài
logging.getLogger("discord").setLevel(logging.WARNING)
logging.getLogger("discord.http").setLevel(logging.WARNING)
logging.getLogger("discord.ui.view").setLevel(logging.ERROR)
logging.getLogger("aiosqlite").setLevel(logging.WARNING)
logging.getLogger("asyncio").setLevel(logging.WARNING)

log = logging.getLogger("bot")

# ══════════════════════════════════════════════════════

COGS = [
    "cogs.combat_task",  # auto-combat queue (load trước)
    "cogs.cong_phap",   # CONG_PHAP data + CongPhapView
    "cogs.hoso",        # /hoso — toàn bộ gameplay qua button
    "cogs.give",        # /give * — admin/owner only
    "cogs.thuoc_tinh",  # /thuoctính — xem thuộc tính chi tiết
    "cogs.reset",       # /reset — user tự wipe nhân vật (tối đa 3 lần)
    "cogs.admin_log",   # /adminlog — xuất log giao dịch Excel (owner only)
    "cogs.world_chat",  # /worldchat — kênh thế giới liên server
    "cogs.vote",        # /vote — biểu quyết toàn server (owner only)
    "cogs.shop",        # /shop, /gencode, /redeem — promo code system
]

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(
    command_prefix="!",
    intents=intents,
    help_command=None,
    chunk_guilds_at_startup=False,   # tránh fetch toàn bộ member lúc start
)


async def setup_hook_fn():
    await init_db()
    # Load cogs ở đây — chỉ chạy 1 lần, không bị gọi lại khi reconnect
    loaded = []
    for cog in COGS:
        try:
            await bot.load_extension(cog)
            loaded.append(f"  ✅ {cog}")
            log.info(f"Loaded cog: {cog}")
        except Exception as e:
            loaded.append(f"  ❌ {cog}: {e}")
            log.error(f"Failed to load cog {cog}: {e}", exc_info=True)
    # Register persistent views cho boss spawn (buttons survive restart)
    try:
        from cogs.views.boss import BossSpawnView
        from utils.config import BOSS_THE_GIOI
        for boss in BOSS_THE_GIOI:
            bot.add_view(BossSpawnView(boss["id"]))
        log.info(f"Registered {len(BOSS_THE_GIOI)} BossSpawnView(s)")
    except Exception as e:
        log.warning(f"BossSpawnView register failed: {e}")
    banner = "\n".join(["", "=" * 50, "🌟 Thiên Đạo v3.0", "=" * 50] + loaded + ["=" * 50])
    log.info(banner)

bot.setup_hook = setup_hook_fn

_ready_once = False
_last_tree_resync_ts = 0.0

async def _sync_commands():
    """Sync slash commands — chỉ gọi khi thực sự cần (thêm/sửa command).
    Có retry với exponential backoff để tránh Cloudflare rate limit.
    """
    for attempt in range(3):
        try:
            synced = await bot.tree.sync()
            log.info(f"Synced {len(synced)} slash commands")
            return
        except discord.HTTPException as e:
            if e.status == 429:
                wait = 60 * (2 ** attempt)  # 60s, 120s, 240s
                log.warning(f"Sync rate limited (attempt {attempt+1}/3), chờ {wait}s...")
                await asyncio.sleep(wait)
            else:
                log.error(f"Sync error: {e}", exc_info=True)
                return
        except Exception as e:
            log.error(f"Sync error: {e}", exc_info=True)
            return
    log.error("Sync thất bại sau 3 lần thử — bỏ qua, dùng /sync khi cần")


async def _sync_if_outdated():
    """Chỉ sync khi remote command tree thiếu command local."""
    try:
        remote_cmds = await bot.tree.fetch_commands()
    except Exception as e:
        log.warning(f"Không fetch được remote commands để đối chiếu: {e}")
        return

    local_names = {c.name for c in bot.tree.get_commands()}
    remote_names = {c.name for c in remote_cmds}
    missing_on_remote = sorted(local_names - remote_names)

    if missing_on_remote:
        log.warning(f"Remote thiếu commands: {missing_on_remote} -> đang sync")
        await _sync_commands()
    else:
        log.info("Slash command tree đã đồng bộ (không cần sync)")

@bot.event
async def on_ready():
    global _ready_once
    # on_ready có thể fire nhiều lần khi reconnect — chỉ làm việc nhẹ
    await setup_emojis(bot)
    if not _ready_once:
        _ready_once = True
        # Chỉ sync khi env var SYNC_ON_START=1 (mặc định OFF)
        # Slash commands đã được Discord lưu — không cần sync mỗi lần restart
        if os.environ.get("SYNC_ON_START") == "1":
            log.info("SYNC_ON_START=1, đang sync commands...")
            asyncio.create_task(_sync_commands())
        else:
            log.info("SYNC_ON_START không set — bỏ qua auto-sync (dùng /sync nếu cần)")
            # Auto-heal: chỉ sync nếu phát hiện remote thiếu command local
            asyncio.create_task(_sync_if_outdated())
    await bot.change_presence(activity=discord.Activity(
        type=discord.ActivityType.playing, name="Tu Tiên | /hoso"
    ))
    log.info(f"Bot ready: {bot.user} | {len(bot.guilds)} servers")
    print(f"🤖 {bot.user} | {len(bot.guilds)} servers\n")


@bot.tree.command(name="sync", description="[Owner] Force sync slash commands")
async def sync_cmd(inter: discord.Interaction):
    from utils.config import OWNER_IDS
    if inter.user.id not in OWNER_IDS:
        return await inter.response.send_message("❌ Chỉ owner mới dùng được!", ephemeral=True)
    await inter.response.defer(ephemeral=True)
    try:
        synced = await bot.tree.sync()
        await safe_followup(inter, f"✅ Synced **{len(synced)}** slash commands globally!", ephemeral=True)
    except Exception as e:
        await safe_followup(inter, f"❌ Sync error: {e}", ephemeral=True)


@bot.tree.error
async def on_tree_error(inter: discord.Interaction, error: discord.app_commands.AppCommandError):
    """Bắt lỗi ở command tree (trước khi vào callback command)."""
    global _last_tree_resync_ts

    if isinstance(error, discord.app_commands.CommandNotFound):
        # Thường xảy ra khi local tree lệch so với command đã đăng ký trên Discord.
        # Log nhẹ + thử tự sync theo nhịp (debounce) để tránh spam/429.
        now = time.time()
        if now - _last_tree_resync_ts >= 600:  # tối đa 1 lần / 10 phút
            _last_tree_resync_ts = now
            log.warning("CommandNotFound trên tree -> schedule auto-sync (debounced)")
            asyncio.create_task(_sync_commands())
        else:
            log.debug("CommandNotFound trên tree (đã debounce sync)")

        try:
            if not inter.response.is_done():
                await inter.response.send_message(
                    "⚠️ Lệnh đang được cập nhật, vui lòng thử lại sau vài giây.",
                    ephemeral=True,
                )
        except Exception:
            pass
        return

    # Lỗi tree khác: giữ log để debug
    log.error("Unhandled tree error", exc_info=error)


@bot.event
async def on_error(event: str, *args, **kwargs):
    log.error(f"Unhandled error in event '{event}'", exc_info=True)


@bot.event
async def on_app_command_error(inter: discord.Interaction, error: discord.app_commands.AppCommandError):
    # Log đầy đủ traceback
    log.error(
        f"AppCommandError | user={inter.user} ({inter.user.id}) "
        f"| cmd=/{inter.command.name if inter.command else '?'} "
        f"| {type(error).__name__}: {error}",
        exc_info=error
    )
    msg = f"Lỗi: {error}"
    try:
        if inter.response.is_done():
            await safe_followup(inter, f"❌ {msg}", ephemeral=True)
        else:
            await inter.response.send_message(f"❌ {msg}", ephemeral=True)
    except Exception:
        log.exception("Lỗi bot")


@bot.event
async def on_guild_join(guild: discord.Guild):
    """Bot được thêm vào server mới."""
    log.info(f"[GuildJoin] {guild.name} (id={guild.id}, members={guild.member_count})")
    # Gửi hướng dẫn vào system channel hoặc channel đầu tiên có quyền
    embed = discord.Embed(
        title="Thiên Đạo v3.0",
        description=(
            "Cảm ơn đã mời ta vào thiên hạ của ngươi!\n\n"
            "⚔️ Dùng `/hoso` để bắt đầu tu tiên\n"
            "🌍 World Boss spawn mỗi 6 tiếng\n"
            "🗺️ Khám phá Bí Cảnh để nhận tài nguyên\n\n"
            "**Admin:** Dùng `/setbosschannel` để chọn channel Boss TG"
        ),
        color=0xF0A500
    )
    ch = guild.system_channel
    if ch and ch.permissions_for(guild.me).send_messages:
        try:
            await ch.send(embed=embed)
        except Exception:
            log.exception("Lỗi bot")

@bot.event
async def on_guild_remove(guild: discord.Guild):
    """Bot bị kick khỏi server."""
    log.info(f"[GuildRemove] {guild.name} (id={guild.id})")


async def main():
    # Health check server cho Railway/Render (port từ env hoặc 8080)
    import aiohttp
    from aiohttp import web

    async def health_check(request):
        return web.Response(text=f"OK | guilds={len(bot.guilds)} | latency={bot.latency*1000:.0f}ms")

    _health_app = web.Application()
    _health_app.router.add_get("/", health_check)
    _health_app.router.add_get("/health", health_check)
    _runner = web.AppRunner(_health_app)
    await _runner.setup()
    _port = int(os.environ.get("PORT", 8080))
    _site = web.TCPSite(_runner, "0.0.0.0", _port)
    await _site.start()
    log.info(f"Health check server running on port {_port}")

    async with bot:
        try:
            log.info("Bot starting...")
            await bot.start(TOKEN)
        except (KeyboardInterrupt, asyncio.CancelledError):
            pass
        except discord.HTTPException as e:
            if e.status == 429:
                # Cloudflare rate limit — chờ trước khi Railway restart
                log.critical(f"Bot bị Cloudflare rate limit (429). Chờ 120s trước khi restart...")
                await asyncio.sleep(120)
            else:
                log.critical(f"Bot crashed (HTTP {e.status}): {e}", exc_info=True)
        except Exception as e:
            log.critical(f"Bot crashed: {e}", exc_info=True)
        finally:
            log.info("Bot shutting down...")
            print("\n[Bot] Đang tắt...")
            await close_db()
            log.info("Bot shutdown complete.")
            print("[Bot] Đã tắt xong.")


if __name__ == "__main__":
    if TOKEN == "YOUR_TOKEN_HERE":
        print("❌ Chưa có token!\n   Set: BOT_TOKEN=xxx python bot.py\n   Hoặc sửa TOKEN trong utils/config.py")
        sys.exit(1)
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
