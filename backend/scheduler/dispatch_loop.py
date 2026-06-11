"""
自动调度循环 — 后台常驻协程

生命周期：
    1. FastAPI lifespan 启动 dispatch_loop.start()
    2. 每 10 秒执行一次 tick
    3. 每个 tick 分三步：推进充电 → 排队→等待 → 等待→充电
    4. FastAPI 关闭时 dispatch_loop.stop()

当前为框架空壳，待后续阶段逐步实现具体逻辑。
"""

import asyncio
import logging

logger = logging.getLogger("dispatch_loop")


class DispatchLoop:
    """自动调度循环 — 后台常驻协程"""

    def __init__(self):
        self._task: asyncio.Task | None = None
        self._running = False

    async def start(self):
        """启动调度循环。"""
        self._running = True
        self._task = asyncio.create_task(self._loop())
        logger.info("自动调度循环已启动 (间隔 10s)")

    async def stop(self):
        """停止调度循环。"""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("自动调度循环已停止")

    async def _loop(self):
        """调度主循环。"""
        while self._running:
            try:
                await self._tick()
            except Exception as e:
                logger.error(f"调度 tick 异常: {e}", exc_info=True)
            await asyncio.sleep(10)

    async def _tick(self):
        """单次调度 tick — 按顺序执行三个步骤。"""
        await self._tick_charging()
        await self._dispatch_queue_to_waiting()
        await self._dispatch_waiting_to_charging()

    async def _tick_charging(self):
        """推进充电进度（待实现）。"""
        pass

    async def _dispatch_queue_to_waiting(self):
        """排队区 → 等待区（待实现）。"""
        pass

    async def _dispatch_waiting_to_charging(self):
        """等待区 → 充电区（待实现）。"""
        pass
