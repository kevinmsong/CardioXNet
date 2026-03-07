import asyncio

from app.services.gtex_client import GTExClient, CardiacExpressionProfile


def test_batch_cardiac_specificity_reuses_cached_profiles(monkeypatch):
    client = GTExClient()
    cached_profile = CardiacExpressionProfile(
        gene_symbol="SRC",
        cardiac_median_tpm=10.0,
        cardiac_mean_tpm=9.0,
        max_non_cardiac_tpm=2.0,
        cardiac_specificity_ratio=5.0,
        total_tissues=54,
        cardiac_rank=1,
    )
    client._cardiac_specificity_cache["SRC"] = cached_profile

    calls = []

    async def fake_calculate(gene_symbol: str):
        calls.append(gene_symbol)
        return CardiacExpressionProfile(
            gene_symbol=gene_symbol,
            cardiac_median_tpm=4.0,
            cardiac_mean_tpm=3.5,
            max_non_cardiac_tpm=1.0,
            cardiac_specificity_ratio=4.0,
            total_tissues=54,
            cardiac_rank=2,
        )

    monkeypatch.setattr(client, "calculate_cardiac_specificity", fake_calculate)

    profiles = asyncio.run(client.batch_cardiac_specificity(["SRC", "MAPK1", "SRC"]))

    assert profiles["SRC"] is cached_profile
    assert profiles["MAPK1"].gene_symbol == "MAPK1"
    assert calls == ["MAPK1"]
