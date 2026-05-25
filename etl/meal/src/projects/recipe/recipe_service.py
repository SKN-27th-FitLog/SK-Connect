import glob
import logging
import os
from datetime import datetime

from src.core.registry import get_collector, get_parser
from src.core.storage.jsonl_writer import JsonlWriter
from src.core.storage.path_builder import HivePathBuilder
from src.core.utils.menu_normalizer import MENU_STATUS_NORMALIZED

logger = logging.getLogger("recipe_project")

MAX_RECIPES_PER_KEYWORD = 3


class RecipeService:
    @staticmethod
    async def run_recipe(category_cd: str) -> dict:
        """
        Process Stage3의 NORMALIZED 메뉴를 읽어
        만개의레시피 레시피 수집 → 파싱 → 저장.
        """
        logger.info(f"--- Starting RECIPE Project: {category_cd} ---")
        dt = datetime.now()

        # 1. Stage3 success JSONL 탐색
        base_path = HivePathBuilder.build_stage_base_path(
            process="normalized", service="shop", category_cd=category_cd,
            stage="validation_normalization", status="success", dt=dt,
        )
        normalized_files = glob.glob(
            os.path.join(base_path, "validation_normalization_*.jsonl")
        )

        if not normalized_files:
            logger.info("No normalized data found for recipe collection.")
            return {"collected": 0, "failed": 0}

        # 2. NORMALIZED 메뉴에서 recipe_search_keyword 추출 (중복 제거)
        seen_keywords: set[str] = set()
        recipe_targets: list[dict] = []

        for file_path in normalized_files:
            for record in JsonlWriter.read(file_path):
                batch_id = record.get("batch_id", "unknown")
                for menu in record.get("menus", []):
                    if menu.get("menu_normalization_status") != MENU_STATUS_NORMALIZED:
                        continue
                    keyword = menu.get("recipe_search_keyword", "").strip()
                    if not keyword or keyword in seen_keywords:
                        continue
                    seen_keywords.add(keyword)
                    recipe_targets.append({"keyword": keyword, "batch_id": batch_id})

        if not recipe_targets:
            logger.info("No NORMALIZED menus with recipe_search_keyword found.")
            return {"collected": 0, "failed": 0}

        logger.info(f"Found {len(recipe_targets)} unique recipe keywords to collect.")

        # 3. 키워드별 레시피 URL 탐색 → 상세 페이지 수집 → 파싱
        collector = get_collector("Recipe10000")
        parser = get_parser("Recipe10000")

        success_results: list[dict] = []
        fail_results: list[dict] = []

        for target in recipe_targets:
            keyword = target["keyword"]
            batch_id = target["batch_id"]

            try:
                recipe_urls = await collector.discover_recipes(
                    keyword, limit=MAX_RECIPES_PER_KEYWORD
                )
                if not recipe_urls:
                    logger.warning(f"No recipe URLs found for keyword: {keyword}")
                    continue

                for recipe_url in recipe_urls:
                    try:
                        raw = await collector.collect(
                            recipe_url, recipe_search_keyword=keyword
                        )
                        html = raw.get("raw_content", "")
                        metadata = parser.parse_recipe_metadata(html)
                        ingredients = parser.parse_ingredients(html)

                        success_results.append({
                            "batch_id": batch_id,
                            "category_cd": category_cd,
                            "recipe_search_keyword": keyword,
                            "recipe_url": recipe_url,
                            **metadata,
                            "ingredients": ingredients,
                            "collected_at": dt.isoformat(),
                        })
                    except Exception as e:
                        logger.warning(f"Recipe detail failed for '{recipe_url}': {e}")
                        fail_results.append({
                            "batch_id": batch_id,
                            "category_cd": category_cd,
                            "recipe_search_keyword": keyword,
                            "recipe_url": recipe_url,
                            "error": str(e),
                            "collected_at": dt.isoformat(),
                        })

            except Exception as e:
                logger.warning(f"Recipe discovery failed for keyword '{keyword}': {e}")

        # 4. 결과 저장
        ref_batch_id = recipe_targets[0]["batch_id"]

        if success_results:
            succ_path = HivePathBuilder.build_path(
                process="recipe", service="shop", category_cd=category_cd,
                stage="recipe_collection", batch_id=ref_batch_id, status="success", dt=dt,
            )
            succ_filename = HivePathBuilder.build_filename(
                "jsonl", dt, stage="recipe_collection",
                batch_id=ref_batch_id, run_attempt=1,
            )
            JsonlWriter.write(succ_path, succ_filename, success_results)
            logger.info(f"Saved {len(success_results)} recipe records.")

        if fail_results:
            fail_path = HivePathBuilder.build_path(
                process="recipe", service="shop", category_cd=category_cd,
                stage="recipe_collection", batch_id=ref_batch_id, status="fail", dt=dt,
            )
            fail_filename = HivePathBuilder.build_filename(
                "jsonl", dt, stage="recipe_collection",
                batch_id=ref_batch_id, run_attempt=1, suffix="fail",
            )
            JsonlWriter.write(fail_path, fail_filename, fail_results)

        logger.info(f"--- RECIPE Project Finished ---")
        return {"collected": len(success_results), "failed": len(fail_results)}
