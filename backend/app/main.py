from fastapi import FastAPI
from starlette.responses import JSONResponse

from app.api.routes import router
from app.api.accounts import router as accounts_router
from app.api.admin import router as admin_router
from app.api.admin_data import router as admin_data_router

app = FastAPI(title="GPS Tracking & Fleet Intelligence", version="0.1.0")


class BodyLimit:
    def __init__(self, app, max_bytes=262144):
        self.app, self.max_bytes = app, max_bytes

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)
        chunks, size = [], 0
        while True:
            message = await receive()
            if message["type"] == "http.disconnect":
                return
            size += len(message.get("body", b""))
            if size > self.max_bytes:
                return await JSONResponse({"detail": "Payload exceeds 256 KiB"}, status_code=413)(scope, receive, send)
            chunks.append(message.get("body", b""))
            if not message.get("more_body", False):
                break
        delivered = False

        async def buffered_receive():
            nonlocal delivered
            if not delivered:
                delivered = True
                return {"type": "http.request", "body": b"".join(chunks), "more_body": False}
            return await receive()

        await self.app(scope, buffered_receive, send)


app.add_middleware(BodyLimit)
app.include_router(router)
app.include_router(accounts_router)
app.include_router(admin_router)
app.include_router(admin_data_router)
