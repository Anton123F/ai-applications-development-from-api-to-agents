import uvicorn

from t11_mcp_auth.mcp_server._server import mcp
from t11_mcp_auth.mcp_server.auth.oauth import JWTAuthMiddleware

#TODO:
# 1. Create the Starlette app by calling `mcp.streamable_http_app()` and assign to `app`
# 2. Add `JWTAuthMiddleware` to the app
app = mcp.streamable_http_app()
app.add_middleware(JWTAuthMiddleware)

if __name__ == "__main__":
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8008,
        log_level="info"
    )