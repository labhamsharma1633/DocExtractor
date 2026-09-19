"""Initial schema

Revision ID: 0001_initial_schema
Revises: 
Create Date: 2026-09-19 12:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0001_initial_schema'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Users table
    op.create_table(
        'users',
        sa.Column('id', sa.Uuid(as_uuid=True), primary_key=True),
        sa.Column('email', sa.String(255), unique=True, nullable=False),
        sa.Column('hashed_password', sa.String(255), nullable=False),
        sa.Column('full_name', sa.String(255), nullable=True),
        sa.Column('is_active', sa.Boolean(), default=True, nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index('ix_users_email', 'users', ['email'], unique=True)

    # Documents table
    op.create_table(
        'documents',
        sa.Column('id', sa.Uuid(as_uuid=True), primary_key=True),
        sa.Column('user_id', sa.Uuid(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('filename', sa.String(255), nullable=False),
        sa.Column('stored_filename', sa.String(255), nullable=False),
        sa.Column('mime_type', sa.String(100), nullable=False),
        sa.Column('file_size_bytes', sa.Integer(), nullable=False),
        sa.Column('page_count', sa.Integer(), default=0, nullable=False),
        sa.Column('processing_status', sa.String(50), default='UPLOADED', nullable=False),
        sa.Column('processing_stage', sa.String(50), default='INIT', nullable=False),
        sa.Column('overall_confidence', sa.Float(), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index('ix_documents_user_id', 'documents', ['user_id'])
    op.create_index('ix_documents_processing_status', 'documents', ['processing_status'])

    # Document Pages table
    op.create_table(
        'document_pages',
        sa.Column('id', sa.Uuid(as_uuid=True), primary_key=True),
        sa.Column('document_id', sa.Uuid(as_uuid=True), sa.ForeignKey('documents.id', ondelete='CASCADE'), nullable=False),
        sa.Column('page_number', sa.Integer(), nullable=False),
        sa.Column('extracted_text', sa.Text(), default='', nullable=False),
        sa.Column('ocr_used', sa.Boolean(), default=False, nullable=False),
        sa.Column('ocr_confidence', sa.Float(), nullable=True),
        sa.Column('image_path', sa.String(500), nullable=True),
        sa.Column('rotation', sa.Integer(), default=0, nullable=False),
        sa.Column('page_metadata', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index('ix_document_pages_document_id', 'document_pages', ['document_id'])

    # Document Relationships table
    op.create_table(
        'document_relationships',
        sa.Column('id', sa.Uuid(as_uuid=True), primary_key=True),
        sa.Column('source_document_id', sa.Uuid(as_uuid=True), sa.ForeignKey('documents.id', ondelete='CASCADE'), nullable=False),
        sa.Column('related_document_id', sa.Uuid(as_uuid=True), sa.ForeignKey('documents.id', ondelete='CASCADE'), nullable=False),
        sa.Column('relationship_type', sa.String(50), default='ANSWER_KEY', nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index('ix_document_relationships_source_id', 'document_relationships', ['source_document_id'])
    op.create_index('ix_document_relationships_related_id', 'document_relationships', ['related_document_id'])

    # Questions table
    op.create_table(
        'questions',
        sa.Column('id', sa.Uuid(as_uuid=True), primary_key=True),
        sa.Column('document_id', sa.Uuid(as_uuid=True), sa.ForeignKey('documents.id', ondelete='CASCADE'), nullable=False),
        sa.Column('question_number', sa.String(50), nullable=True),
        sa.Column('question_text', sa.Text(), nullable=False),
        sa.Column('question_type', sa.String(50), default='MCQ', nullable=False),
        sa.Column('confidence_score', sa.Float(), default=1.0, nullable=False),
        sa.Column('extraction_status', sa.String(50), default='EXTRACTED', nullable=False),
        sa.Column('matched_answer', sa.Text(), nullable=True),
        sa.Column('answer_source', sa.String(50), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index('ix_questions_document_id', 'questions', ['document_id'])

    # Question Options table
    op.create_table(
        'question_options',
        sa.Column('id', sa.Uuid(as_uuid=True), primary_key=True),
        sa.Column('question_id', sa.Uuid(as_uuid=True), sa.ForeignKey('questions.id', ondelete='CASCADE'), nullable=False),
        sa.Column('option_key', sa.String(10), nullable=False),
        sa.Column('option_text', sa.Text(), nullable=False),
        sa.Column('is_correct', sa.Boolean(), nullable=True),
        sa.Column('order_index', sa.Integer(), default=0, nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index('ix_question_options_question_id', 'question_options', ['question_id'])

    # Question Sources table
    op.create_table(
        'question_sources',
        sa.Column('id', sa.Uuid(as_uuid=True), primary_key=True),
        sa.Column('question_id', sa.Uuid(as_uuid=True), sa.ForeignKey('questions.id', ondelete='CASCADE'), nullable=False),
        sa.Column('page_number', sa.Integer(), nullable=False),
        sa.Column('bounding_box', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index('ix_question_sources_question_id', 'question_sources', ['question_id'])

    # Answer Keys table
    op.create_table(
        'answer_keys',
        sa.Column('id', sa.Uuid(as_uuid=True), primary_key=True),
        sa.Column('document_id', sa.Uuid(as_uuid=True), sa.ForeignKey('documents.id', ondelete='CASCADE'), nullable=False),
        sa.Column('raw_key_text', sa.Text(), default='', nullable=False),
        sa.Column('parsed_answers', sa.JSON(), nullable=False),
        sa.Column('page_number', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index('ix_answer_keys_document_id', 'answer_keys', ['document_id'])

    # Review Items table
    op.create_table(
        'review_items',
        sa.Column('id', sa.Uuid(as_uuid=True), primary_key=True),
        sa.Column('document_id', sa.Uuid(as_uuid=True), sa.ForeignKey('documents.id', ondelete='CASCADE'), nullable=False),
        sa.Column('question_id', sa.Uuid(as_uuid=True), sa.ForeignKey('questions.id', ondelete='SET NULL'), nullable=True),
        sa.Column('review_type', sa.String(50), nullable=False),
        sa.Column('severity', sa.String(20), default='MEDIUM', nullable=False),
        sa.Column('message', sa.Text(), nullable=False),
        sa.Column('confidence', sa.Float(), nullable=True),
        sa.Column('is_resolved', sa.Boolean(), default=False, nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index('ix_review_items_document_id', 'review_items', ['document_id'])
    op.create_index('ix_review_items_question_id', 'review_items', ['question_id'])


def downgrade() -> None:
    op.drop_table('review_items')
    op.drop_table('answer_keys')
    op.drop_table('question_sources')
    op.drop_table('question_options')
    op.drop_table('questions')
    op.drop_table('document_relationships')
    op.drop_table('document_pages')
    op.drop_table('documents')
    op.drop_table('users')
