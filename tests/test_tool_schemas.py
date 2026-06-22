from app.agent.tool_schemas import trade_tools


def test_trade_tools_returns_three_tools():
    tools = trade_tools(["BTC/USDT", "ETH/USDT"])
    names = [t["function"]["name"] for t in tools]
    assert names == ["place_order", "close_position", "hold"]


def test_symbol_enum_is_restricted_to_allowlist():
    tools = trade_tools(["BTC/USDT"])
    place_order = tools[0]
    enum = place_order["function"]["parameters"]["properties"]["symbol"]["enum"]
    assert enum == ["BTC/USDT"]
    # для close_position тоже enum
    close = tools[1]
    assert close["function"]["parameters"]["properties"]["symbol"]["enum"] == ["BTC/USDT"]


def test_required_fields_are_marked():
    tools = trade_tools(["X/USDT"])
    place_order = tools[0]["function"]["parameters"]
    assert set(place_order["required"]) == {"symbol", "side", "quote_amount", "reason"}
    assert place_order["additionalProperties"] is False
