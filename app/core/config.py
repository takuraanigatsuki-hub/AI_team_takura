from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Annotated, Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


PROJECT_ROOT = Path(__file__).resolve().parents[2]


def _parse_csv(value: str | list[str] | None) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(v).strip() for v in value if str(v).strip()]
    return [item.strip() for item in str(value).split(",") if item.strip()]


class Settings(BaseSettings):
    # --- App -------------------------------------------------------------
    app_name: str = "Trade"
    host: str = "0.0.0.0"
    port: int = 8000
    debug: bool = True
    log_level: str = "INFO"

    # --- DB --------------------------------------------------------------
    database_url: str = f"sqlite:///{PROJECT_ROOT / 'data' / 'trade.db'}"

    # --- Exchange & instruments -----------------------------------------
    exchange_id: str = "binance"
    quote_currency: str = "USDT"
    symbols: Annotated[list[str], NoDecode] = Field(
        default_factory=lambda: ["BTC/USDT", "ETH/USDT", "SOL/USDT"]
    )
    timeframe: str = "15m"
    loop_interval_seconds: int = 30

    # --- Mode ------------------------------------------------------------
    mode: Literal["paper", "live"] = "paper"
    paper_starting_balance: float = 10_000.0

    exchange_api_key: str = ""
    exchange_api_secret: str = ""
    exchange_api_password: str = ""
    exchange_testnet: bool = False

    # --- Risk ------------------------------------------------------------
    risk_per_trade: float = 0.05
    max_open_positions: int = 3
    stop_loss_pct: float = 0.03
    take_profit_pct: float = 0.06
    daily_loss_limit_pct: float = 0.05
    min_order_notional: float = 10.0

    # --- Strategies ------------------------------------------------------
    strategies: Annotated[list[str], NoDecode] = Field(
        default_factory=lambda: ["ma_crossover", "rsi_reversion", "bollinger_breakout"]
    )
    signal_consensus: int = 2

    # --- LLM advisor -----------------------------------------------------
    # Дефолт — топовая reasoning-модель OpenAI (gpt-5.4-high).
    # Альтернативы (через OpenRouter, LLM_PROVIDER=openrouter):
    #   anthropic/claude-opus-4.8         — самый сильный reasoning от Anthropic
    #   anthropic/claude-4.6-sonnet       — баланс цена/качество
    #   openai/gpt-5.4-high               — то же самое через OpenRouter
    # Для локального инференса: LLM_BASE_URL=http://localhost:11434/v1
    llm_provider: str = "openai"
    llm_api_key: str = ""
    llm_model: str = "gpt-5.4-high"
    llm_base_url: str = ""  # пусто = дефолт провайдера

    # Native function-calling (OpenAI tools API) вместо JSON-mode.
    # Сильно надёжнее на frontier-моделях. На моделях, не поддерживающих
    # tools, агент автоматически деградирует в JSON-mode.
    llm_use_tools: bool = True

    # --- Autonomous agent ------------------------------------------------
    agent_enabled: bool = False
    agent_interval_seconds: int = 600  # как часто LLM-агент принимает решение
    agent_max_actions_per_cycle: int = 3
    agent_news_per_cycle: int = 8
    agent_journal_lookback: int = 6  # сколько прошлых записей дневника подмешивать в контекст
    agent_temperature: float = 0.2
    agent_max_tokens: int = 1500

    # --- Reflection ------------------------------------------------------
    # Раз в N часов агент перечитывает свой дневник, оценивает выполненные
    # сделки и пишет memo c уроками. Memo подмешивается в промпт следующих
    # циклов — простая форма «обучения без ML».
    reflection_enabled: bool = True
    reflection_interval_hours: int = 12
    reflection_journal_lookback: int = 30
    reflection_max_tokens: int = 800
    reflection_temperature: float = 0.4

    # --- Web auth --------------------------------------------------------
    web_user: str = ""
    web_password: str = ""

    # --- Telegram --------------------------------------------------------
    telegram_bot_token: str = ""
    telegram_chat_id: str = ""
    telegram_notify_orders: bool = True
    telegram_notify_agent: bool = True
    telegram_notify_errors: bool = True
    telegram_daily_summary_hour_utc: int = 9

    model_config = SettingsConfigDict(
        env_file=str(PROJECT_ROOT / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    @field_validator("symbols", "strategies", mode="before")
    @classmethod
    def _split_csv(cls, value):  # noqa: ANN001
        return _parse_csv(value)

    @field_validator("mode", mode="before")
    @classmethod
    def _lower_mode(cls, value):  # noqa: ANN001
        if isinstance(value, str):
            return value.strip().lower()
        return value


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()


def reset_settings_cache() -> None:
    """Mostly for tests — drop the cached Settings so envs reload."""
    get_settings.cache_clear()
