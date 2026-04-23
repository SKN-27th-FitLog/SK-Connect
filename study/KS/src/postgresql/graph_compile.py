from langgraph.graph import StateGraph, START, END
from connection import PGVectorStoreState
from graph_noeds import search_vectordb_node, evaluate_vectordb_node, rewriting_question_node, tavily_search_node, create_answer_node


#############################################
# PG VectorDB 그래프 분기 조건 
#############################################
def is_eval_yes(state:PGVectorStoreState)-> str:
    if state['evaluation_result'] == "yes":
        return "create_answer_node"

    return "rewriting_question_node"


#############################################
# PG VectorDB 그래프 작성 
#############################################
def create_graph():
    """ PG VectorDB 그래프 작성 함수 """
    # Set State
    workflow = StateGraph(PGVectorStoreState)

    # Add Nodes
    workflow.add_node(search_vectordb_node, "search_vectordb")
    workflow.add_node(evaluate_vectordb_node, "evaluate_vectordb")
    workflow.add_node(rewriting_question_node, "rewriting_question")
    workflow.add_node(tavily_search_node, "tavily_search")
    workflow.add_node(create_answer_node, "create_answer")

    # Link Edges
    workflow.add_edge(START, "search_vectordb")
    workflow.add_edge("search_vectordb", "evaluate_vectordb")

    # => Conditional Edges
    workflow.add_conditional_edges(
        "evaluate_vectordb",
        is_eval_yes,
        {
            "create_answer_node":"create_answer_node",
            "rewriting_question_node":"rewriting_question_node"
        }
    )

    workflow.add_edge("rewriting_question_node","tavily_search_node")
    workflow.add_edge("tavily_search_node","create_answer_node")
    workflow.add_edge("create_answer_node",END)


    return workflow.compile()
