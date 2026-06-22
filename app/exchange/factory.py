from __future__ import annotations

from ..core.config import Settings, get_settings
from .base import BaseExchange, ExchangeError
from .paper import PaperExchange


def build_exchange(settings: Settings | None = None) -> BaseExchange:
    """Создаёт биржу согласно настройкам.

    - mode='paper' → PaperExchange (виртуальные деньги) поверх данных ccxt.
    - mode='live'  → CCXTExchange с выставлением реальных ордеров.
    """
    settings = settings or get_settings()

    from .ccxt_exchange import CCXTExchange

    if settings.mode == "live":
        if not (settings.exchange_api_key and settings.exchange_api_secret):
            raise ExchangeError(
                "live mode requires EXCHANGE_API_KEY and EXCHANGE_API_SECRET"
            )
        return CCXTExchange(
            exchange_id=settings.exchange_id,
            api_key=settings.exchange_api_key,
            api_secret=settings.exchange_api_secret,
            api_password=settings.exchange_api_password,
            testnet=settings.exchange_testnet,
            mode="live",
        )

    # paper mode — данные берём из публичного ccxt-клиента без ключей
    data_source = CCXTExchange(
        exchange_id=settings.exchange_id,
        testnet=settings.exchange_testnet,
        mode="paper",
    )
    return PaperExchange(
        data_source=data_source,
        quote_currency=settings.quote_currency,
        starting_balance=settings.paper_starting_balance,
    )
