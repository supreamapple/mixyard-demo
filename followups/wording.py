from dataclasses import dataclass


@dataclass(frozen=True)
class TradeWording:
    """Words a shop actually says. The planner never hard-codes a trade."""

    job_noun: str
    job_noun_plural: str
    quantity_unit: str
    quote_noun: str


def concrete_wording() -> TradeWording:
    return TradeWording(
        job_noun="pour",
        job_noun_plural="pours",
        quantity_unit="yards",
        quote_noun="quote",
    )
