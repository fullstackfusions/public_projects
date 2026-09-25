# /// script
# requires-python = ">=3.11"
# dependencies = ["mcp>=2.2,<3"]
# ///
"""Smoke test: start server.py over stdio like an agent would and call every tool.

    CHAPERONE_API_URL=... AWS_PROFILE=... uv run --script smoke_test.py
"""
import asyncio, os, pathlib, time
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
SERVER = str(pathlib.Path(__file__).with_name("server.py"))
async def main():
    p = StdioServerParameters(command="uv", args=["run", "--quiet", "--script", SERVER], env={**os.environ})
    async with stdio_client(p) as (r, w):
        async with ClientSession(r, w) as s:
            init = await s.initialize()
            print("server:", init.server_info.name)
            tools = await s.list_tools()
            print("tools:", [t.name for t in tools.tools])
            for name, args in [("list_sessions", {"days": 2, "agents_only": True}),
                               ("what_did_the_agent_do", {}), ("risky_calls", {}),
                               ("review_session", {}), ("least_privilege", {}),
                               ("risky_calls", {"session_id": "nobody@2026-01-01T00:00:00Z"})]:
                t = time.time()
                res = await s.call_tool(name, args)
                text = "".join(c.text for c in res.content if hasattr(c, "text"))
                print(f"\n== {name} {args} error={res.is_error} {len(text)}B {time.time()-t:.1f}s")
                print(text[:700])
asyncio.run(main())
