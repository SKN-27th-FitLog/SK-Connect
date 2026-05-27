import pytest

import local_pipeline_runner as runner


@pytest.mark.asyncio
async def test_local_runner_executes_image_validation_between_process_and_recipe(monkeypatch):
    calls = []

    async def fake_run_crawl(platform, category_cd):
        calls.append(("crawl", platform, category_cd))
        return {"batch_id": "20260527_SC01_001"}

    def fake_run_process(platform, category_cd):
        calls.append(("process", platform, category_cd))

    class FakeImageValidationService:
        def run_image_validation(self, category_cd):
            calls.append(("image_validation", category_cd))

    async def fake_run_recipe(category_cd):
        calls.append(("recipe", category_cd))
        return {"processed_batches": ["20260527_SC01_001"]}

    def fake_run_save(category_cd):
        calls.append(("save", category_cd))
        return {"processed_batches": ["20260527_SC01_001"]}

    monkeypatch.setattr(runner.CrawlService, "run_crawl", fake_run_crawl)
    monkeypatch.setattr(runner.ProcessService, "run_process", fake_run_process)
    monkeypatch.setattr(runner, "ImageValidationService", FakeImageValidationService)
    monkeypatch.setattr(runner.RecipeService, "run_recipe", fake_run_recipe)
    monkeypatch.setattr(runner.SaveService, "run_save", fake_run_save)
    monkeypatch.setattr(runner.os, "makedirs", lambda *args, **kwargs: None)
    monkeypatch.setattr(runner.glob, "glob", lambda *args, **kwargs: [])

    batch_id = await runner.run_and_consolidate("DiningCode", "SC01")

    assert batch_id == "20260527_SC01_001"
    assert calls == [
        ("crawl", "DiningCode", "SC01"),
        ("process", "DiningCode", "SC01"),
        ("image_validation", "SC01"),
        ("recipe", "SC01"),
        ("save", "SC01"),
    ]
