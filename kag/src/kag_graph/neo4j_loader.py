from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class CypherFile:
    name: str
    path: Path


def load_cypher_files(driver, database: str, files: list[CypherFile]) -> list[str]:
    loaded: list[str] = []
    with driver.session(database=database) as session:
        for cypher_file in files:
            statements = split_cypher_statements(cypher_file.path.read_text(encoding="utf-8"))
            if not statements:
                continue
            for statement in statements:
                session.run(statement)
            loaded.append(cypher_file.name)

    return loaded


def split_cypher_statements(cypher: str) -> list[str]:
    return [
        f"{statement.strip()};"
        for statement in cypher.split(";")
        if statement.strip()
    ]
