"""Initial schema

Revision ID: 001
Revises: 
Create Date: 2024-01-01 00:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Users
    op.create_table(
        "users",
        sa.Column("id", sa.String(36), nullable=False, primary_key=True),
        sa.Column("username", sa.String(100), nullable=False, unique=True, index=True),
        sa.Column("email", sa.String(255), nullable=False, unique=True, index=True),
        sa.Column("hashed_password", sa.String(255), nullable=False),
        sa.Column("role", sa.String(50), nullable=False, server_default="viewer"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="1"),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("last_login", sa.DateTime(), nullable=True),
    )

    # Documents
    op.create_table(
        "documents",
        sa.Column("id", sa.String(36), nullable=False, primary_key=True),
        sa.Column("filename", sa.String(500), nullable=False),
        sa.Column("original_filename", sa.String(500), nullable=False),
        sa.Column("file_path", sa.String(1000), nullable=False),
        sa.Column("file_size", sa.Integer(), nullable=True),
        sa.Column("mime_type", sa.String(200), nullable=True),
        sa.Column("category", sa.String(100), nullable=False, server_default="unknown"),
        sa.Column("medical_specialty", sa.String(200), nullable=True),
        sa.Column("source", sa.String(500), nullable=True),
        sa.Column("title", sa.String(1000), nullable=True),
        sa.Column("authors", sa.Text(), nullable=True),
        sa.Column("publication_year", sa.Integer(), nullable=True),
        sa.Column("processing_status", sa.String(50), nullable=False, server_default="pending"),
        sa.Column("embedding_status", sa.Boolean(), nullable=False, server_default="0"),
        sa.Column("chunk_count", sa.Integer(), server_default="0"),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("is_validated", sa.Boolean(), nullable=False, server_default="0"),
        sa.Column("validation_score", sa.Float(), nullable=True),
        sa.Column("rejection_reason", sa.Text(), nullable=True),
        sa.Column("uploaded_at", sa.DateTime(), nullable=False),
        sa.Column("processed_at", sa.DateTime(), nullable=True),
        sa.Column("uploaded_by", sa.String(36), sa.ForeignKey("users.id"), nullable=True),
    )

    # Document Chunks
    op.create_table(
        "document_chunks",
        sa.Column("id", sa.String(36), nullable=False, primary_key=True),
        sa.Column("document_id", sa.String(36), sa.ForeignKey("documents.id"), nullable=False),
        sa.Column("chunk_index", sa.Integer(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("embedding_id", sa.String(500), nullable=True),
        sa.Column("page_number", sa.Integer(), nullable=True),
        sa.Column("section", sa.String(500), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )

    # Query Logs
    op.create_table(
        "query_logs",
        sa.Column("id", sa.String(36), nullable=False, primary_key=True),
        sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("query_type", sa.String(100), nullable=False),
        sa.Column("query_text", sa.Text(), nullable=False),
        sa.Column("response_summary", sa.Text(), nullable=True),
        sa.Column("sources_used", sa.Text(), nullable=True),
        sa.Column("confidence_score", sa.Float(), nullable=True),
        sa.Column("response_time_ms", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )

    # Audit Logs
    op.create_table(
        "audit_logs",
        sa.Column("id", sa.String(36), nullable=False, primary_key=True),
        sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("action", sa.String(200), nullable=False),
        sa.Column("resource_type", sa.String(100), nullable=True),
        sa.Column("resource_id", sa.String(36), nullable=True),
        sa.Column("details", sa.Text(), nullable=True),
        sa.Column("ip_address", sa.String(50), nullable=True),
        sa.Column("user_agent", sa.String(500), nullable=True),
        sa.Column("success", sa.Boolean(), nullable=False, server_default="1"),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )

    # Indexes
    op.create_index("ix_documents_category", "documents", ["category"])
    op.create_index("ix_documents_status", "documents", ["processing_status"])
    op.create_index("ix_documents_uploaded_at", "documents", ["uploaded_at"])
    op.create_index("ix_chunks_document_id", "document_chunks", ["document_id"])
    op.create_index("ix_query_logs_user", "query_logs", ["user_id"])
    op.create_index("ix_audit_logs_user", "audit_logs", ["user_id"])


def downgrade() -> None:
    op.drop_table("audit_logs")
    op.drop_table("query_logs")
    op.drop_table("document_chunks")
    op.drop_table("documents")
    op.drop_table("users")
