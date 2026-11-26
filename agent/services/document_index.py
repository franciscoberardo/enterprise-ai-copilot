import hashlib
import json
import os
from pathlib import Path
from threading import RLock
from uuid import uuid4

from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter


class DocumentIndex:
    def __init__(self, store, uploads, manifest):
        self.store = store
        self.uploads = Path(uploads)
        self.manifest = Path(manifest)
        self.lock = RLock()
        self.splitter = RecursiveCharacterTextSplitter(chunk_size=700, chunk_overlap=150)
        self.uploads.mkdir(parents=True, exist_ok=True)

    def sync(self):
        with self.lock:
            previous = json.loads(self.manifest.read_text()) if self.manifest.exists() else {}
            files = {path.name: path for path in sorted(self.uploads.glob("*")) if path.suffix.lower() == ".pdf" and path.is_file()}
            current = {}
            catalog = None

            def records():
                nonlocal catalog
                if catalog is None:
                    catalog = self.store.get(include=["metadatas"])
                return zip(catalog["ids"], catalog["metadatas"])

            for name, path in files.items():
                digest = hashlib.sha256(path.read_bytes()).hexdigest()
                if previous.get(name, {}).get("hash") == digest:
                    current[name] = previous[name]
                    continue

                pages = PyPDFLoader(str(path)).load()
                chunks = self.splitter.split_documents(pages)
                if not chunks:
                    raise ValueError(f"{name}: el PDF no tiene texto extraíble")
                old = [key for key, metadata in records() if Path((metadata or {}).get("source", "")).name == name]
                ids = [hashlib.sha256(f"{name}:{digest}:{index}".encode()).hexdigest() for index in range(len(chunks))]
                for chunk in chunks:
                    chunk.metadata.update(source=str(path), document_hash=digest)
                # Indexa la nueva versión antes de retirar la anterior.
                try:
                    self.store.add_documents(chunks, ids=ids)
                except Exception:
                    try:
                        self.store.delete(ids=list(set(ids) - set(old)))
                    except Exception:
                        pass
                    raise
                stale = list(set(old) - set(ids))
                if stale:
                    self.store.delete(ids=stale)
                current[name] = {"hash": digest, "chunks": len(chunks), "pages": len(pages)}

            removed = set(previous) - set(files)
            if removed:
                ids = [key for key, metadata in records() if Path((metadata or {}).get("source", "")).name in removed]
                if ids:
                    self.store.delete(ids=ids)
            self.manifest.parent.mkdir(parents=True, exist_ok=True)
            if current != previous or not self.manifest.exists():
                temporary = self.manifest.with_suffix(".tmp")
                temporary.write_text(json.dumps(current, ensure_ascii=False, indent=2))
                os.replace(temporary, self.manifest)
            return [{"name": name, **metadata} for name, metadata in current.items()]

    def similarity_search(self, query, k=3):
        with self.lock:
            self.sync()
            return self.store.similarity_search(query, k=k)

    def upload(self, name, data):
        if Path(name).name != name or Path(name).suffix.lower() != ".pdf" or "%PDF-" not in data[:1024].decode("latin1"):
            raise ValueError("Seleccioná un archivo PDF válido, sin rutas en su nombre")
        with self.lock:
            target = self.uploads / name
            if target.resolve().parent != self.uploads.resolve():
                raise ValueError("Ruta de documento inválida")
            old = target.read_bytes() if target.exists() else None
            temporary = self.uploads / f".{uuid4()}.tmp"
            temporary.write_bytes(data)
            os.replace(temporary, target)
            try:
                return self.sync()
            except Exception:
                if old is None:
                    target.unlink(missing_ok=True)
                else:
                    temporary.write_bytes(old)
                    os.replace(temporary, target)
                raise
