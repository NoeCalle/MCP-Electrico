from mcp_electrico import project_report_tools


class FakeMCP:
    def __init__(self):
        self.tools = {}

    def tool(self):
        def decorator(fn):
            self.tools[fn.__name__] = fn
            return fn
        return decorator


def test_p7d_gate_is_exposed_through_existing_p7_tool_registry():
    mcp = FakeMCP()
    project_report_tools.register(mcp)

    assert "evaluar_cierre_p7d_engineering_preview" in mcp.tools
    result = mcp.tools["evaluar_cierre_p7d_engineering_preview"]()
    assert result["product_release"] == "MCP_ELECTRICO_0_9_ENGINEERING_PREVIEW"
    assert result["engineering_preview_ready"] is True
    assert result["professional_emission"] is False
