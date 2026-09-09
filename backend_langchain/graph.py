from typing import TypedDict, List
from langgraph.graph import StateGraph, END
from chains.question_generator import generate_questions
from chains.critic import verify_question
from chains.evaluator import check_grounding
from schemas import Question


class QuizPipelineState(TypedDict):
    document_text: str
    document_id: str
    candidate_questions: List[Question]
    grounded_questions: List[dict]
    verified_questions: List[dict]
    retry_count: int
    max_retries: int
    final_questions: List[dict]


async def generate_node(state: QuizPipelineState) -> QuizPipelineState:
    result = await generate_questions(state["document_text"])
    state["candidate_questions"] = result.questions
    return state


async def grounding_check_node(state: QuizPipelineState) -> QuizPipelineState:
    grounded = []
    for q in state["candidate_questions"]:
        result = check_grounding(q, state["document_text"])
        if result["grounded"]:
            grounded.append(result)
    state["grounded_questions"] = grounded
    return state


async def critic_node(state: QuizPipelineState) -> QuizPipelineState:
    verified = []
    for item in state["grounded_questions"]:
        verdict = await verify_question(item["question"], state["document_text"])
        if verdict["passed"]:
            verified.append({**item, **verdict})
    state["verified_questions"] = verified
    return state


def route_after_critic(state: QuizPipelineState) -> str:
    if (
        len(state["verified_questions"]) == 0
        and state["retry_count"] < state["max_retries"]
    ):
        state["retry_count"] += 1
        return "generate"
    return "finalize"


def finalize_node(state: QuizPipelineState) -> QuizPipelineState:
    state["final_questions"] = state["verified_questions"]
    return state


def build_quiz_pipeline():
    graph = StateGraph(QuizPipelineState)
    graph.add_node("generate", generate_node)
    graph.add_node("grounding_check", grounding_check_node)
    graph.add_node("critic", critic_node)
    graph.add_node("finalize", finalize_node)
    graph.set_entry_point("generate")
    graph.add_edge("generate", "grounding_check")
    graph.add_edge("grounding_check", "critic")
    graph.add_conditional_edges(
        "critic", route_after_critic, {"generate": "generate", "finalize": "finalize"}
    )
    graph.add_edge("finalize", END)
    return graph.compile()


quiz_pipeline = build_quiz_pipeline()


async def run_quiz_pipeline(
    document_text: str, document_id: str, max_retries: int = 1
) -> List[dict]:
    initial_state: QuizPipelineState = {
        "document_text": document_text,
        "document_id": document_id,
        "candidate_questions": [],
        "grounded_questions": [],
        "verified_questions": [],
        "retry_count": 0,
        "max_retries": max_retries,
        "final_questions": [],
    }
    result = await quiz_pipeline.ainvoke(initial_state)
    return result["final_questions"]
