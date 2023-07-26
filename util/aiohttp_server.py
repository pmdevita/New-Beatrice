from aiohttp import web
import alluka
import tanjun
from atsume.settings import settings


def hook_aiohttp_server(c: alluka.Injected[tanjun.Client]) -> None:
    @c.with_client_callback(tanjun.ClientCallbackNames.STARTING)
    async def on_starting(client: alluka.Injected[tanjun.abc.Client]) -> None:
        app = web.Application()
        client.set_type_dependency(web.Application, app)

    @c.with_client_callback(tanjun.ClientCallbackNames.STARTED)
    async def on_start(client: alluka.Injected[tanjun.abc.Client], app: alluka.Injected[web.Application]) -> None:
        task = client.loop.create_task(web._run_app(app, host=settings.WEB_SERVER_HOST, port=settings.WEB_SERVER_PORT))

        @c.with_client_callback(tanjun.ClientCallbackNames.CLOSED)
        async def on_closed() -> None:
            task.cancel()

