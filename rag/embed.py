"""RAG Embedding Pipeline — chunk Indonesian building regulations and embed for retrieval."""

import os
import pdfplumber
import re
from pathlib import Path
from typing import List, Dict
from langchain.text_splitter import RecursiveCharacterTextSplitter
from sentence_transformers import SentenceTransformer
import chromadb
from chromadb.config import Settings
import yaml


class RegulationEmbedder:
    def __init__(self, model_name: str = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"):
        self.model = SentenceTransformer(model_name)
        self.chunks = []
        self.metadatas = []
        self.ids = []
        
    def extract_pdf_text(self, pdf_path: str) -> List[Dict]:
        """Extract text and tables from PDF with page references."""
        documents = []
        with pdfplumber.open(pdf_path) as pdf:
            for page_num, page in enumerate(pdf.pages, start=1):
                text = page.extract_text()
                if text:
                    documents.append({
                        "text": text,
                        "page": page_num,
                        "source": os.path.basename(pdf_path)
                    })
        return documents
    
    def extract_html_regulations(self, html_dir: str) -> List[Dict]:
        """Extract text from downloaded HTML regulation files."""
        documents = []
        for html_file in Path(html_dir).rglob("*.html"):
            with open(html_file, encoding="utf-8") as f:
                content = f.read()
            # Remove HTML tags, keep text
            text = re.sub(r"<[^>]+>", " ", content)
            text = re.sub(r"\s+", " ", text).strip()
            documents.append({
                "text": text,
                "source": str(html_file.name),
                "type": "regulation"
            })
        return documents
    
    def chunk_documents(self, documents: List[Dict], chunk_size: int = 512, chunk_overlap: int = 64):
        """Split documents into overlapping chunks for embedding."""
        splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            length_function=len,
            separators=["\n\n", "\n", ". ", " "]
        )
        
        for doc in documents:
            chunks = splitter.split_text(doc["text"])
            for i, chunk in enumerate(chunks):
                self.chunks.append(chunk)
                self.metadatas.append({
                    "source": doc.get("source", "unknown"),
                    "page": doc.get("page", 0),
                    "chunk_id": i,
                    "type": doc.get("type", "regulation")
                })
                self.ids.append(f"{doc.get('source', 'doc')}_{doc.get('page', 0)}_{i}")
    
    def embed_and_store(self, collection_name: str = "indonesian_regulations", persist_dir: str = "./data/processed"):
        """Embed chunks and store in ChromaDB."""
        os.makedirs(persist_dir, exist_ok=True)
        
        print(f"Embedding {len(self.chunks)} chunks...")
        embeddings = self.model.encode(self.chunks, show_progress_bar=True)
        
        client = chromadb.PersistentClient(path=persist_dir)
        collection = client.create_collection(
            name=collection_name,
            metadata={"description": "Indonesian building regulations and SNI standards"}
        )
        
        collection.add(
            embeddings=embeddings.tolist(),
            documents=self.chunks,
            metadatas=self.metadatas,
            ids=self.ids
        )
        
        print(f"Stored {len(self.chunks)} chunks in ChromaDB collection '{collection_name}'")
        return collection


def main():
    config = yaml.safe_load(open("config.yaml"))
    embedder = RegulationEmbedder()
    
    # Process PDFs from SNI corpus
    sni_dir = config["data"]["sni_corpus"]
    for pdf_file in Path(sni_dir).glob("*.pdf"):
        print(f"Processing {pdf_file}...")
        docs = embedder.extract_pdf_text(str(pdf_file))
        embedder.chunk_documents(docs)
    
    # Process HTML regulations
    reg_dir = config["data"]["regulations"]
    if Path(reg_dir).exists():
        docs = embedder.extract_html_regulations(reg_dir)
        embedder.chunk_documents(docs)
    
    # Store
    embedder.embed_and_store(
        collection_name=config["rag"]["collection_name"],
        persist_dir=config["data"]["processed"]
    )
    print("Embedding pipeline complete!")


if __name__ == "__main__":
    main()