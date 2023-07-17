import asyncio
import traceback

_tasks = set()


def start_background_task(coro):
    async def log_exceptions():
        try:
            await coro
        except Exception as e:
            traceback.print_exc()

    task = asyncio.create_task(log_exceptions())
    _tasks.add(task)
    task.add_done_callback(_tasks.discard)




