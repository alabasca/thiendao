"""
CombatTaskCog — auto-combat runner.
"""
from __future__ import annotations
import asyncio
import logging
import discord
from dataclasses import dataclass, field
from typing import Callable, Awaitable, Any
from discord.ext import commands

log = logging.getLogger("combat_task")


@dataclass
class CombatJob:
    inter:     discord.Interaction
    logs:      list[Any]
    embed_fn:  Callable[[int], discord.Embed]
    view:      discord.ui.View
    on_finish: Callable[[], Awaitable[None]]
    delay:     float = 1.2
    _skip:     bool  = field(default=False, init=False)
    _task:     asyncio.Task[None] | None = field(default=None, init=False)

    def skip(self) -> None:
        self._skip = True


class CombatTaskCog(commands.Cog, name="CombatTaskCog"):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self._running: dict[int, CombatJob] = {}

    async def cog_unload(self) -> None:
        for job in list(self._running.values()):
            if job._task and not job._task.done():
                job._task.cancel()

    def enqueue(self, job: CombatJob) -> None:
        uid = job.inter.user.id
        old = self._running.get(uid)
        if old and old._task and not old._task.done():
            old._task.cancel()
        task = asyncio.ensure_future(self._run_job(job))
        job._task = task
        self._running[uid] = job
        task.add_done_callback(
            lambda t: self._running.pop(uid, None) if self._running.get(uid) is job else None)

    def skip_current(self, user_id: int) -> None:
        job = self._running.get(user_id)
        if job:
            job.skip()

    async def _run_job(self, job: CombatJob) -> None:
        total = len(job.logs)
        log.info(f"Combat start: user={job.inter.user.id} turns={total}")

        for n in range(1, total + 1):
            if job._skip:
                break

            # Bỏ qua frame ll_tick — không có gì thay đổi về mặt hiển thị
            if job.logs[n - 1][1] == "ll_tick":
                continue

            # Tạo embed — bắt lỗi riêng để biết rõ nguyên nhân
            try:
                emb = job.embed_fn(n)
            except Exception as e:
                log.error(f"Combat embed_fn error turn={n}: {e}", exc_info=True)
                return

            # Edit message
            try:
                await job.inter.edit_original_response(embed=emb, view=job.view)
            except discord.NotFound:
                log.warning(f"Combat message not found, finishing user={job.inter.user.id}")
                break  # message mất → thoát loop nhưng vẫn gọi on_finish để lưu thưởng
            except discord.HTTPException as e:
                if e.status == 429:
                    retry = float(e.response.headers.get("Retry-After", "2"))
                    log.warning(f"Combat rate limit, retry after {retry}s")
                    await asyncio.sleep(retry)
                    try:
                        await job.inter.edit_original_response(embed=emb, view=job.view)
                    except Exception as e2:
                        log.error(f"Combat retry failed: {e2}")
                        break  # vẫn gọi on_finish
                else:
                    log.error(f"Combat HTTP {e.status}: {e.text}")
                    break  # vẫn gọi on_finish
            except asyncio.CancelledError:
                return  # bị cancel chủ động → KHÔNG gọi on_finish (đúng)
            except Exception as e:
                log.error(f"Combat edit error turn={n}: {e}", exc_info=True)
                break  # vẫn gọi on_finish



            try:
                await asyncio.sleep(job.delay)
            except asyncio.CancelledError:
                return

        log.info(f"Combat done, calling on_finish user={job.inter.user.id}")
        try:
            await job.on_finish()
        except Exception as e:
            log.error(f"Combat on_finish error: {e}", exc_info=True)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(CombatTaskCog(bot))
