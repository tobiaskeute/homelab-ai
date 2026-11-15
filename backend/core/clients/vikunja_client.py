"""
Vikunja client that connects to the official MCP server.

Provides LangGraph-compatible tools for integrating Vikunja via its MCP endpoint.
"""
from fastmcp.client import BearerAuth
from langchain.mcp import MCPAdapter

from fastmcp import Client


class VikunjaAdapter(MCPAdapter):
    def __init__(self, base_url, mcp_token):
        self.base_url = base_url
        self.mcp_token = mcp_token
        self._client = self._create_client()
        super().__init__(self.client)

    @property
    def _mcp_url(self):
        return f"{self.base_url.rstrip('/')}/api/v2/mcp"

    def _create_client(self):
        return Client(
            transport=self._mcp_url,
            auth=BearerAuth(self.mcp_token)
        )

    #@override
    #def list_tools(self, *, cache_mode: CacheMode = "use") -> list[BaseTool]:
    #    async def _async_tools():
    #        return await super(VikunjaAdapter, self).list_tools(cache_mode=cache_mode)#
    #
    #    return asyncio.run(_async_tools())
