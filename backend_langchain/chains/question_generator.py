from langchain_core.prompts import ChatPromptTemplate
from config import gemini
from schemas import ConceptList, QuestionList

concept_extraction_prompt = ChatPromptTemplate.from_template(
    "다음 텍스트에서 핵심 개념들을 추출해주세요.\n\n텍스트:\n{text}\n\n각 개념에 대해 이름, 설명, 중요도(0.0~1.0)를 포함해주세요."
)
concept_chain = concept_extraction_prompt | gemini.with_structured_output(ConceptList)
question_generation_prompt = ChatPromptTemplate.from_template(
    "다음 핵심 개념들을 바탕으로 문제를 생성해주세요.\n\n핵심 개념:\n{concepts}\n\n원본 텍스트:\n{text}\n\n다음 지침을 엄격히 따라주세요:\n1. 정확히 3개의 객관식 문제를 생성하세요.\n2. 각 문제는 반드시 텍스트 내용과 추출된 핵심 개념에 기반해야 합니다.\n3. 각 문제는 4개의 보기를 가져야 합니다.\n4. 정답은 반드시 보기 중 하나여야 합니다.\n5. 해설은 왜 그 답이 정답인지 명확히 설명해야 합니다.\n6. 각 문제의 난이도는 개념의 중요도를 반영해야 합니다.\n7. 표나 그림을 참조하는 문제는 내지 마세요."
)
question_chain = question_generation_prompt | gemini.with_structured_output(
    QuestionList
)


async def generate_questions(text: str) -> QuestionList:
    concepts = await concept_chain.ainvoke({"text": text})
    questions = await question_chain.ainvoke(
        {"concepts": concepts.model_dump_json(), "text": text}
    )
    validated = [q for q in questions.questions if q.correct_answer in q.options]
    return QuestionList(questions=validated)
