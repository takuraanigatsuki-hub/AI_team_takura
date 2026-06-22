"""JSON Schemas инструментов агента для native function-calling (OpenAI tools API).

Те же три инструмента, что доступны и в JSON-mode (place_order, close_position,
hold), но описанные как OpenAI tools spec. На моделях, поддерживающих tools,
это даёт строгую валидацию схемы и заметно надёжнее парсинга свободного JSON.
"""
from __future__ import annotations


def trade_tools(allowed_symbols: list[str]) -> list[dict]:
    """Вернуть массив tools для передачи в chat.completions.

    Symbol enum жёстко ограничен списком разрешённых пар — модель физически
    не сможет запросить покупку «случайной» монеты вне портфельной вселенной.
    """
    symbol_schema = {"type": "string", "enum": list(allowed_symbols)} if allowed_symbols else {"type": "string"}
    return [
        {
            "type": "function",
            "function": {
                "name": "place_order",
                "description": (
                    "Открыть или долить позицию рыночным ордером. "
                    "quote_amount — сумма в котировочной валюте (USDT), не количество базового актива. "
                    "Риск-менеджер обрежет ордер до допустимого размера; даже если quote_amount великоват, "
                    "он будет ужат до RISK_PER_TRADE * equity."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "symbol": symbol_schema,
                        "side": {"type": "string", "enum": ["buy", "sell"]},
                        "quote_amount": {
                            "type": "number",
                            "exclusiveMinimum": 0,
                            "description": "Сумма в котировочной валюте (USDT).",
                        },
                        "reason": {
                            "type": "string",
                            "maxLength": 280,
                            "description": "Краткое обоснование со ссылкой на конкретные числа (VaR, β, сентимент).",
                        },
                    },
                    "required": ["symbol", "side", "quote_amount", "reason"],
                    "additionalProperties": False,
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "close_position",
                "description": "Полностью закрыть открытую позицию по символу (продать всё).",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "symbol": symbol_schema,
                        "reason": {"type": "string", "maxLength": 280},
                    },
                    "required": ["symbol", "reason"],
                    "additionalProperties": False,
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "hold",
                "description": (
                    "Ничего не делать в этом цикле. Это легитимное и часто правильное действие — "
                    "если конъюнктура неясна или риск выше допустимого, лучше hold."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "reason": {"type": "string", "maxLength": 280},
                    },
                    "required": ["reason"],
                    "additionalProperties": False,
                },
            },
        },
    ]
