"""
MediRAG AI – Bulk Indexing Script
Re-indexes all documents that have been processed but not yet embedded.
Run: python scripts/index_existing.py
"""

import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import select
from app.models.database import AsyncSessionLocal, init_db, Document, ProcessingStatus
from app.vectorstore.vector_store_manager import VectorStoreManager


async def index_all():
    await init_db()
    vsm = VectorStoreManager()

    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(Document).where(
                Document.processing_status == ProcessingStatus.INDEXED,
                Document.embedding_status == False,
            )
        )
        docs = result.scalars().all()

        if not docs:
            print("No documents pending indexing.")
            return

        print(f"Found {len(docs)} document(s) to index.")
        for doc in docs:
            print(f"  Indexing: {doc.original_filename}...", end=" ")
            try:
                count = await vsm.index_document(doc.id, session)
                print(f"{count} chunks indexed.")
            except Exception as exc:
                print(f"FAILED: {exc}")

        await session.commit()
        print("Done.")


if __name__ == "__main__":
    asyncio.run(index_all())
