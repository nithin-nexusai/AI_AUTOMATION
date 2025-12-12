"""initial_schema

Revision ID: c4f8f2e06cf5
Revises:
Create Date: 2025-12-11 08:12:39.016847

Simplified schema for CHICX AI Platform:
- Products and Orders are NOT stored locally (fetched from CHICX API)
- Only stores: users, conversations, messages, calls, faqs, embeddings, search_logs
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from pgvector.sqlalchemy import Vector

# revision identifiers, used by Alembic.
revision: str = 'c4f8f2e06cf5'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Enable pgvector extension
    op.execute('CREATE EXTENSION IF NOT EXISTS vector')

    # ==========================================================================
    # Core tables (no foreign keys)
    # ==========================================================================

    # Users - minimal, just for conversation tracking
    op.create_table('users',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('phone', sa.String(length=20), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_users_phone'), 'users', ['phone'], unique=True)

    # FAQs - knowledge base for semantic search
    op.create_table('faqs',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('question', sa.Text(), nullable=False),
        sa.Column('answer', sa.Text(), nullable=False),
        sa.Column('category', sa.String(length=100), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_faqs_category'), 'faqs', ['category'], unique=False)

    # Embeddings - pgvector for FAQ semantic search
    op.create_table('embeddings',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('source_type', sa.Enum('faq', name='sourcetype'), nullable=False),
        sa.Column('source_id', sa.UUID(), nullable=False),
        sa.Column('chunk_text', sa.Text(), nullable=False),
        sa.Column('embedding', Vector(1536), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_embeddings_source_id'), 'embeddings', ['source_id'], unique=False)
    op.create_index(op.f('ix_embeddings_source_type'), 'embeddings', ['source_type'], unique=False)

    # Templates - WhatsApp message templates
    op.create_table('templates',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('type', sa.Enum('utility', 'marketing', name='templatetype'), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('meta_template_id', sa.String(length=100), nullable=True),
        sa.Column('status', sa.Enum('pending', 'approved', 'rejected', name='templatestatus'), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('name')
    )

    # ==========================================================================
    # Tables with foreign keys
    # ==========================================================================

    # Conversations - chat/call sessions
    op.create_table('conversations',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('user_id', sa.UUID(), nullable=False),
        sa.Column('channel', sa.Enum('whatsapp', 'voice', name='channeltype'), nullable=False),
        sa.Column('status', sa.Enum('active', 'closed', 'escalated', name='conversationstatus'), nullable=False),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('ended_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('metadata', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_conversations_user_id'), 'conversations', ['user_id'], unique=False)

    # Messages - individual messages in conversations
    op.create_table('messages',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('conversation_id', sa.UUID(), nullable=False),
        sa.Column('role', sa.Enum('user', 'assistant', 'system', name='messagerole'), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('message_type', sa.Enum('text', 'image', 'audio', 'template', name='messagetype'), nullable=False),
        sa.Column('wa_message_id', sa.String(length=100), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['conversation_id'], ['conversations.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_messages_conversation_id'), 'messages', ['conversation_id'], unique=False)
    op.create_index(op.f('ix_messages_created_at'), 'messages', ['created_at'], unique=False)
    op.create_index(op.f('ix_messages_wa_message_id'), 'messages', ['wa_message_id'], unique=False)

    # Calls - voice call records
    op.create_table('calls',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('conversation_id', sa.UUID(), nullable=True),
        sa.Column('user_id', sa.UUID(), nullable=True),
        sa.Column('phone', sa.String(length=20), nullable=False),
        sa.Column('exotel_call_id', sa.String(length=100), nullable=True),
        sa.Column('bolna_call_id', sa.String(length=100), nullable=True),
        sa.Column('direction', sa.Enum('inbound', 'outbound', name='calldirection'), nullable=False),
        sa.Column('status', sa.Enum('resolved', 'escalated', 'missed', 'failed', name='callstatus'), nullable=False),
        sa.Column('duration_seconds', sa.Integer(), nullable=True),
        sa.Column('recording_url', sa.String(length=500), nullable=True),
        sa.Column('language', sa.String(length=10), nullable=True),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('ended_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['conversation_id'], ['conversations.id'], ),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_calls_conversation_id'), 'calls', ['conversation_id'], unique=False)
    op.create_index(op.f('ix_calls_exotel_call_id'), 'calls', ['exotel_call_id'], unique=True)
    op.create_index(op.f('ix_calls_bolna_call_id'), 'calls', ['bolna_call_id'], unique=True)
    op.create_index(op.f('ix_calls_phone'), 'calls', ['phone'], unique=False)
    op.create_index(op.f('ix_calls_user_id'), 'calls', ['user_id'], unique=False)

    # Call Transcripts - voice call transcriptions
    op.create_table('call_transcripts',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('call_id', sa.UUID(), nullable=False),
        sa.Column('transcript', sa.Text(), nullable=False),
        sa.Column('segments', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['call_id'], ['calls.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('call_id')
    )

    # Analytics Events - event tracking
    op.create_table('analytics_events',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('user_id', sa.UUID(), nullable=True),
        sa.Column('event_type', sa.String(length=100), nullable=False),
        sa.Column('event_data', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_analytics_events_created_at'), 'analytics_events', ['created_at'], unique=False)
    op.create_index(op.f('ix_analytics_events_event_type'), 'analytics_events', ['event_type'], unique=False)
    op.create_index(op.f('ix_analytics_events_user_id'), 'analytics_events', ['user_id'], unique=False)

    # Search Logs - for catalog gap analysis
    op.create_table('search_logs',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('query', sa.String(length=255), nullable=False),
        sa.Column('language', sa.String(length=10), nullable=True),
        sa.Column('results_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('user_id', sa.UUID(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_search_logs_created_at'), 'search_logs', ['created_at'], unique=False)
    op.create_index(op.f('ix_search_logs_query'), 'search_logs', ['query'], unique=False)


def downgrade() -> None:
    # Drop tables in reverse order (respect foreign keys)
    op.drop_index(op.f('ix_search_logs_query'), table_name='search_logs')
    op.drop_index(op.f('ix_search_logs_created_at'), table_name='search_logs')
    op.drop_table('search_logs')

    op.drop_index(op.f('ix_analytics_events_user_id'), table_name='analytics_events')
    op.drop_index(op.f('ix_analytics_events_event_type'), table_name='analytics_events')
    op.drop_index(op.f('ix_analytics_events_created_at'), table_name='analytics_events')
    op.drop_table('analytics_events')

    op.drop_table('call_transcripts')

    op.drop_index(op.f('ix_calls_user_id'), table_name='calls')
    op.drop_index(op.f('ix_calls_phone'), table_name='calls')
    op.drop_index(op.f('ix_calls_bolna_call_id'), table_name='calls')
    op.drop_index(op.f('ix_calls_exotel_call_id'), table_name='calls')
    op.drop_index(op.f('ix_calls_conversation_id'), table_name='calls')
    op.drop_table('calls')

    op.drop_index(op.f('ix_messages_wa_message_id'), table_name='messages')
    op.drop_index(op.f('ix_messages_created_at'), table_name='messages')
    op.drop_index(op.f('ix_messages_conversation_id'), table_name='messages')
    op.drop_table('messages')

    op.drop_index(op.f('ix_conversations_user_id'), table_name='conversations')
    op.drop_table('conversations')

    op.drop_table('templates')

    op.drop_index(op.f('ix_embeddings_source_type'), table_name='embeddings')
    op.drop_index(op.f('ix_embeddings_source_id'), table_name='embeddings')
    op.drop_table('embeddings')

    op.drop_index(op.f('ix_faqs_category'), table_name='faqs')
    op.drop_table('faqs')

    op.drop_index(op.f('ix_users_phone'), table_name='users')
    op.drop_table('users')

    # Drop enums
    op.execute('DROP TYPE IF EXISTS sourcetype')
    op.execute('DROP TYPE IF EXISTS templatetype')
    op.execute('DROP TYPE IF EXISTS templatestatus')
    op.execute('DROP TYPE IF EXISTS channeltype')
    op.execute('DROP TYPE IF EXISTS conversationstatus')
    op.execute('DROP TYPE IF EXISTS messagerole')
    op.execute('DROP TYPE IF EXISTS messagetype')
    op.execute('DROP TYPE IF EXISTS calldirection')
    op.execute('DROP TYPE IF EXISTS callstatus')
