from neo4j import Driver

from kag_graph.models import EvidencePathDTO, GraphNodeDTO, GraphRelationshipDTO, GraphSearchResultDTO, QueryBuildResult


def node_to_dto(node) -> GraphNodeDTO:
    return GraphNodeDTO(labels=list(node.labels), properties=dict(node))


def relationship_to_dto(relationship, nodes_by_id: dict[int, GraphNodeDTO]) -> GraphRelationshipDTO:
    return GraphRelationshipDTO(
        type=relationship.type,
        start_node=nodes_by_id[relationship.start_node.id],
        end_node=nodes_by_id[relationship.end_node.id],
        properties=dict(relationship),
    )


def path_to_dto(path) -> EvidencePathDTO | None:
    if path is None:
        return None

    nodes = [node_to_dto(node) for node in path.nodes]
    nodes_by_id = {node.id: node_to_dto(node) for node in path.nodes}
    relationships = [
        relationship_to_dto(relationship, nodes_by_id)
        for relationship in path.relationships
    ]
    return EvidencePathDTO(nodes=nodes, relationships=relationships)


class Neo4jRepository:
    def __init__(self, driver: Driver, database: str):
        self._driver = driver
        self._database = database

    def run_query(self, query: QueryBuildResult) -> list[GraphSearchResultDTO]:
        with self._driver.session(database=self._database) as session:
            result = session.run(query.query_text, query.params)
            return [self._record_to_result(record) for record in result]

    def _record_to_result(self, record) -> GraphSearchResultDTO:
        evidence_paths = [
            path_dto
            for path_dto in (path_to_dto(path) for path in record["evidence_paths"])
            if path_dto is not None
        ]
        return GraphSearchResultDTO(
            result_node=node_to_dto(record["result_node"]),
            evidence_paths=evidence_paths,
            score=float(record["score"]),
        )
