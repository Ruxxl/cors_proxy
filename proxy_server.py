import os
import aiohttp
from aiohttp import web
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("CORS_Proxy")

CORS_HEADERS = {
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS",
    "Access-Control-Allow-Headers": "Content-Type, Authorization, X-Requested-With",
}

async def proxy_handler(request):
    if request.method == "OPTIONS":
        return web.Response(status=200, headers=CORS_HEADERS)

    target_url = request.query.get("url")
    if not target_url:
        return web.json_response({"error": "No URL provided"}, status=400, headers=CORS_HEADERS)

    # Читаем тело запроса
    body = await request.read()
    
    # Копируем заголовки, НО удаляем те, что заставляют сервер сжимать ответ
    headers = {k: v for k, v in request.headers.items() if k.lower() not in ["host", "accept-encoding"]}

    try:
        # auto_decompress=True поможет, если сервер проигнорирует наш запрет на сжатие
        async with aiohttp.ClientSession(auto_decompress=True) as session:
            async with session.request(
                method=request.method,
                url=target_url,
                headers=headers,
                data=body,
                timeout=60
            ) as response:
                
                content = await response.read()
                
                # Собираем заголовки для ответа браузеру
                resp_headers = dict(response.headers)
                resp_headers.update(CORS_HEADERS)
                
                # Удаляем старые транспортные заголовки, чтобы браузер не запутался
                resp_headers.pop("Content-Encoding", None)
                resp_headers.pop("Transfer-Encoding", None)
                resp_headers.pop("Content-Length", None) 

                return web.Response(
                    body=content,
                    status=response.status,
                    headers=resp_headers
                )

    except Exception as e:
        logger.error(f"Proxy error: {e}")
        return web.json_response({"error": str(e)}, status=502, headers=CORS_HEADERS)

async def init_app():
    app = web.Application()
    app.router.add_route("*", "/proxy", proxy_handler)
    app.router.add_get("/", lambda r: web.Response(text="Proxy is active"))
    return app

if __name__ == "__main__":
    app = init_app()
    web.run_app(app, host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))
