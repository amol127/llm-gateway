
PRICES: dict[str, tuple[float, float]] = {}
DEFAULT_PRICE = (1.0, 3.0)

def cost_usd(model: str, input_tokens: int, output_tokens: int) -> float:
    in_price, out_price = PRICES.get(model, DEFAULT_PRICE)
    return (input_tokens * in_price + output_tokens * out_price) / 1_000_000


