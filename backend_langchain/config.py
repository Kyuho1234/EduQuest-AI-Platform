import os
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_openai import ChatOpenAI
from langchain_huggingface import HuggingFaceEmbeddings

load_dotenv()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
DATABASE_URL = os.getenv(
    "VECTOR_DATABASE_URL",
    "postgresql+psycopg://user:pass@113.198.66.75:13229/db1_database",
)
gemini = ChatGoogleGenerativeAI(
    model="gemini-2.0-flash", google_api_key=GEMINI_API_KEY, temperature=0.7
)
deepseek_critic = ChatOpenAI(
    model="deepseek/deepseek-chat-v3-0324:free",
    base_url="https://openrouter.ai/api/v1",
    api_key=OPENROUTER_API_KEY,
    temperature=0.1,
    default_headers={
        "HTTP-Referer": "http://localhost:3000",
        "X-Title": "EduQuest Quiz Generator",
    },
)
qwen_critic = ChatOpenAI(
    model="qwen/qwen3-235b-a22b:free",
    base_url="https://openrouter.ai/api/v1",
    api_key=OPENROUTER_API_KEY,
    temperature=0.1,
    default_headers={
        "HTTP-Referer": "http://localhost:3000",
        "X-Title": "EduQuest Quiz Generator",
    },
)
embeddings = HuggingFaceEmbeddings(model_name="jhgan/ko-sroberta-multitask")
GROUNDING_THRESHOLD = 0.4
