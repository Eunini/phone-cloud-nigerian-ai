"""Marginal inference/data cost; hardware, electricity and model download are separate."""


def cost_per_1000(
    *,
    placement,
    mb_per_question,
    ngn_per_mb,
    usage=None,
    input_usd_per_million=None,
    output_usd_per_million=None,
    usd_to_ngn=None,
    free_tier=False,
    measured_cloud_usd_per_question=None,
):
    if placement not in {"local", "cloud"} or min(mb_per_question, ngn_per_mb) < 0:
        raise ValueError("Invalid placement or negative cost input")
    if placement == "local":
        return {
            "data_ngn": 0.0,
            "api_ngn": 0.0,
            "total_ngn": 0.0,
            "scope": "marginal data/API cost; excludes hardware, power, model download",
        }
    data = 1000 * mb_per_question * ngn_per_mb
    if free_tier:
        api = 0.0
    elif measured_cloud_usd_per_question is not None:
        if measured_cloud_usd_per_question < 0 or usd_to_ngn is None or usd_to_ngn <= 0:
            raise ValueError("Measured self-hosting cost needs a positive exchange rate")
        api = 1000 * measured_cloud_usd_per_question * usd_to_ngn
    else:
        if any(
            x is None for x in [usage, input_usd_per_million, output_usd_per_million, usd_to_ngn]
        ):
            raise ValueError("Token billing needs observed usage, both rates, and an exchange rate")
        if min(input_usd_per_million, output_usd_per_million) < 0 or usd_to_ngn <= 0:
            raise ValueError("Invalid billing rate")
        api = (
            (
                usage["prompt_tokens"] * input_usd_per_million
                + usage["completion_tokens"] * output_usd_per_million
            )
            / 1_000_000
            * 1000
            * usd_to_ngn
        )
    return {
        "data_ngn": data,
        "api_ngn": api,
        "total_ngn": data + api,
        "scope": "marginal inference and application-body mobile data",
    }


def cheapest_eligible(rows, threshold):
    if not 0 <= threshold <= 1:
        raise ValueError("Accuracy threshold must be in [0, 1]")
    candidates = [r for r in rows if r["accuracy"] >= threshold and r.get("cost_ngn") is not None]
    return min(candidates, key=lambda r: (r["cost_ngn"], -r["accuracy"])) if candidates else None
