"""Environment based configuration, without embedded secrets."""
import os
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class Settings:
    port: int = int(os.getenv("PORT", "8000"))
    environment: str = os.getenv("ENVIRONMENT", "development")
    agent_api_key: str = os.getenv("AGENT_API_KEY", "")
    redis_url: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    rate_limit_per_minute: int = int(os.getenv("RATE_LIMIT_PER_MINUTE", "10"))
    daily_budget_usd: float = float(os.getenv("DAILY_BUDGET_USD", "1.0"))
    price_input_per_1k: float = float(os.getenv("PRICE_INPUT_PER_1K", "0.00015"))
    price_output_per_1k: float = float(os.getenv("PRICE_OUTPUT_PER_1K", "0.0006"))


settings = Settings()
