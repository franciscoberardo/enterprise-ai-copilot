from pathlib import Path


def retrieve_documents(vectorstore, query):
    fragments = []
    for document in vectorstore.similarity_search(query, k=3):
        filename = Path(document.metadata.get("source", "")).name
        page = document.metadata.get("page")
        fragments.append({
            "document": filename if filename.lower().endswith(".pdf") else None,
            "page": page + 1 if isinstance(page, int) and page >= 0 else None,
            "text": document.page_content,
        })
    return {"fragments": fragments}
