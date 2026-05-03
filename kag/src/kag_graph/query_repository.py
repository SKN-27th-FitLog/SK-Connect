from pathlib import Path


class QueryTemplateNotFoundError(KeyError):
    pass


class QueryRepository:
    def __init__(self, template_paths: dict[str, Path]):
        self._template_paths = template_paths

    def get(self, template_name: str) -> str:
        path = self._template_paths.get(template_name)
        if path is None:
            raise QueryTemplateNotFoundError(template_name)

        return path.read_text(encoding="utf-8").strip()
