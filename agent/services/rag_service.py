from pathlib import Path

from langchain_community.vectorstores import Chroma

from models import embeddings
from services.document_index import DocumentIndex

UPLOADS = Path(__file__).parent.parent.parent / "backend" / "uploads"
DB_DIR = Path(__file__).parent.parent / "vectorstore"

vectorstore = DocumentIndex(
    Chroma(persist_directory=str(DB_DIR), embedding_function=embeddings),
    UPLOADS,
    DB_DIR / "documents.json",
)
vectorstore.sync()
