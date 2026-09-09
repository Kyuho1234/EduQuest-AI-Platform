from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnableParallel
from config import deepseek_critic, qwen_critic
from schemas import CriticVerdict, Question

critic_prompt = ChatPromptTemplate.from_template(
    "주어진 문제가 입력 자료를 정확하게 반영하는지 평가해주세요.\n\n[입력 자료]\n{context}\n\n[평가할 문제]\n질문: {question}\n보기: {options}\n정답: {correct_answer}\n해설: {explanation}\n\n[평가 기준]\n1. 입력 자료 참고도: 문제와 답이 입력 자료에 근거하는가?\n2. 문제 품질: 문제가 명확하고 적절한가?\n\n당신은 교육 분야의 전문가이자 엄격한 평가자입니다."
)
dual_critic_chain = RunnableParallel(
    deepseek_verdict=critic_prompt
    | deepseek_critic.with_structured_output(CriticVerdict),
    qwen_verdict=critic_prompt | qwen_critic.with_structured_output(CriticVerdict),
)


async def verify_question(question: Question, context: str) -> dict:
    inputs = {
        "context": context,
        "question": question.question,
        "options": ", ".join(question.options),
        "correct_answer": question.correct_answer,
        "explanation": question.explanation,
    }
    try:
        result = await dual_critic_chain.ainvoke(inputs)
        deepseek_v = result["deepseek_verdict"]
        qwen_v = result["qwen_verdict"]
        dual_verified = deepseek_v.passed and qwen_v.passed
        return {
            "question": question,
            "passed": dual_verified,
            "deepseek_verdict": deepseek_v,
            "qwen_verdict": qwen_v,
            "feedback": (
                deepseek_v.feedback
                if dual_verified
                else "두 모델의 검증 결과가 불일치하여 문제가 탈락되었습니다."
            ),
        }
    except Exception as e:
        return {
            "question": question,
            "passed": False,
            "deepseek_verdict": None,
            "qwen_verdict": None,
            "feedback": f"검증 중 오류가 발생했습니다: {str(e)}",
        }
