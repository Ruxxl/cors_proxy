import os
import aiohttp
from aiohttp import web
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("CORS_Proxy")

# Разрешенные заголовки для CORS
CORS_HEADERS = {
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS",
    "Access-Control-Allow-Headers": "Content-Type, Authorization, X-Requested-With",
}

async def handle_options(request):
    """Обработка preflight-запросов OPTIONS от браузера."""
    return web.Response(status=200, headers=CORS_HEADERS)

async def proxy_handler(request):
    """Основной обработчик, который пересылает запросы."""
    # Обработка OPTIONS
    if request.method == "OPTIONS":
        return await handle_options(request)

    # Получаем целевой URL из заголовка или параметров запроса
    # Браузер будет слать запрос на: http://proxy/proxy?url=https://api.confluence.com/...
    target_url = request.query.get("url")
    
    if not target_url:
        return web.json_response(
            {"error": "Missing 'url' parameter in query string"}, 
            status=400, 
            headers=CORS_HEADERS
        )

    logger.info(f"Проксирование запроса {request.method} на: {target_url}")

    # Читаем тело оригинального запроса
    body = await request.read()
    
    # Копируем заголовки от браузера
    headers = {k: v for k, v in request.headers.items() if k.lower() != "host"}
    
    # КРИТИЧЕСКИЙ МОМЕНТ: Удаляем просьбу о сжатии, 
    # чтобы сервер прислал нам обычный JSON (plain text)
    headers.pop("Accept-Encoding", None)

    try:
        # Указываем aiohttp НЕ пытаться автоматически декодировать сжатие
        async with aiohttp.ClientSession(auto_decompress=False) as session:
            async with session.request(
                method=request.method,
                url=target_url,
                headers=headers,
                data=body,
                timeout=30
            ) as response:
                
                response_body = await response.read()
                
                # Формируем заголовки ответа
                proxy_response_headers = dict(response.headers)
                proxy_response_headers.update(CORS_HEADERS)
                
                # Удаляем заголовки, которые теперь неактуальны (так как мы получили сырые данные)
                proxy_response_headers.pop("Content-Encoding", None)
                proxy_response_headers.pop("Transfer-Encoding", None)
                proxy_response_headers.pop("Content-Length", None) # Пусть aiohttp пересчитает сам

                return web.Response(
                    body=response_body,
                    status=response.status,
                    headers=proxy_response_headers
                )

    except Exception as e:
        logger.error(f"Ошибка при проксировании: {e}")
        return web.json_response(
            {"error": f"Proxy error: {str(e)}"}, 
            status=502, 
            headers=CORS_HEADERS
        )

async def init_app():
    app = web.Application()
    # Любой запрос, пришедший на /proxy, будет перенаправлен
    app.router.add_route("*", "/proxy", proxy_handler)
    
    # Хелсчек для Render
    app.router.add_get("/", lambda r: web.Response(text="Proxy is running!"))
    return app

if __name__ == "__main__":
    app = init_app()
    port = int(os.environ.get("PORT", 8081))
    web.run_app(app, host="0.0.0.0", port=port)
