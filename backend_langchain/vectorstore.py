from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_postgres import PGVector
from langchain_core.documents import Document
from config import embeddings, DATABASE_URL

splitter = RecursiveCharacterTextSplitter(
    chunk_size=450,
    chunk_overlap=100,
    separators=["\n\n", "\n", ". ", "! ", "? ", " ", ""],
)
vectorstore = PGVector(
    embeddings=embeddings,
    collection_name="eduquest_document_chunks",
    connection=DATABASE_URL,
    use_jsonb=True,
)


def ingest_pdf(file_path: str, document_id: str, filename: str) -> list[Document]:
    loader = PyPDFLoader(file_path)
    raw_docs = loader.load()
    chunks = splitter.split_documents(raw_docs)
    for i, chunk in enumerate(chunks):
        chunk.metadata.update(
            {"document_id": document_id, "filename": filename, "chunk_index": i}
        )
    vectorstore.add_documents(chunks)
    return chunks


def get_full_document_text(document_id: str) -> str:
    results = vectorstore.similarity_search(
        query="", k=1000, filter={"document_id": document_id}
    )
    results.sort(key=lambda d: d.metadata.get("chunk_index", 0))
    return "\n".join((d.page_content for d in results))


def get_retriever(document_id: str, k: int = 5):
    return vectorstore.as_retriever(
        search_kwargs={"k": k, "filter": {"document_id": document_id}}
    )
