import asyncio
import os
from typing import List
from agno.knowledge.pdf import PDFKnowledgeBase
from agno.vectordb.lancedb import LanceDb
from agno.vectordb.search import SearchType
from agno.knowledge.pdf_url import PDFUrlKnowledgeBase
from agno.embedder.fastembed import FastEmbedEmbedder
#from agno.vectordb.pgvector import PgVector



class DermaKnowledgeBase:
    def __init__(self, table_name: str, db_path: str, pdf_paths: List[str], urls: List[str]):
        full_path = os.path.join(db_path, table_name)  # LanceDB expects the path to the collection

        self.vector_db = LanceDb(
            table_name=table_name,
            uri=db_path,  # pass just the folder root to `uri`
            search_type=SearchType.hybrid,
            embedder=FastEmbedEmbedder()
        )
        self.pdf_paths = pdf_paths
        self.urls = urls
        self.table_name = table_name

    async def aload(self, upsert=True, recreate=False):

    # Update PDF paths to point to the resources folder
        if self.pdf_paths:
            self.pdf_paths = [
                f"/home/wambui_nicole/VisionModel/skin/resources/{os.path.basename(pdf)}"
                for pdf in self.pdf_paths
            ]
            local_kb = PDFKnowledgeBase(path="./resources", vector_db=self.vector_db)        #this is what I changed
            await local_kb.aload(upsert=upsert, recreate=recreate)

        # Load from URLs
        if self.urls:
            url_kb = PDFUrlKnowledgeBase(urls=self.urls, vector_db=self.vector_db)
            await url_kb.aload(upsert=upsert, recreate=recreate)

    def get_knowledge_base(self):
        # Just return one interface (same DB)
        return PDFKnowledgeBase(files=[], vector_db=self.vector_db)
