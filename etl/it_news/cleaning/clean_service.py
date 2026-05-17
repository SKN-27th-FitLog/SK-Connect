from __future__ import annotations

import asyncio
import logging
from typing import Any

from common.constant import ItNewsFilePrefix
from cleaning.cleaning import cleaning_threads

logger = logging.getLogger(__name__)


class CleanService:
    """IT 뉴스 클리닝 실행 서비스."""

    @staticmethod
    async def run_clean(output_csv_prefix: str = ItNewsFilePrefix.DEFAULT) -> dict[str, Any]:
        """클리닝 실행.

        Parameters
        ----------
        output_csv_prefix:
            cleaning 결과 CSV 파일 prefix.
        """

        logger.info(
            "클리닝 시작: output_csv_prefix=%s",
            output_csv_prefix,
        )

        c_ok, c_fail = await asyncio.to_thread(
            cleaning_threads,
            output_csv_prefix=output_csv_prefix,
        )

        logger.info(
            "클리닝 종료: success=%d fail=%d",
            len(c_ok),
            len(c_fail),
        )

        return {
            "step": "clean",
            "output_csv_prefix": output_csv_prefix,
            "success_count": len(c_ok),
            "fail_count": len(c_fail),
        }