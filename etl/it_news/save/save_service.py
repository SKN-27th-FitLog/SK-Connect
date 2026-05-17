from __future__ import annotations

import asyncio
import logging
from typing import Any

from common.constant import ItNewsFilePrefix
from save.save import save_threads

logger = logging.getLogger(__name__)


class SaveService:
    """IT 뉴스 저장 실행 서비스."""

    @staticmethod
    async def run_save(save_file_prefix: str = ItNewsFilePrefix.DEFAULT) -> dict[str, Any]:
        """DB 저장 및 save 결과 CSV 생성.

        Parameters
        ----------
        save_file_prefix:
            save 결과 CSV 파일 prefix.
        """

        logger.info(
            "저장 시작: save_file_prefix=%s",
            save_file_prefix,
        )

        s_ok, s_fail = await asyncio.to_thread(
            save_threads,
            save_file_prefix=save_file_prefix,
        )

        logger.info(
            "저장 종료: success=%d fail=%d",
            len(s_ok),
            len(s_fail),
        )

        return {
            "step": "save",
            "save_file_prefix": save_file_prefix,
            "success_count": len(s_ok),
            "fail_count": len(s_fail),
        }