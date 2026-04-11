"""Integration tests for database operations."""

import pytest
from sqlalchemy import select
from app.models.user import User
from app.models.conversation import Conversation, Message, ChannelType, MessageRole


@pytest.mark.integration
@pytest.mark.database
class TestUserModel:
    """Test User model database operations."""

    @pytest.mark.asyncio
    async def test_create_user(self, test_db_session):
        """Test creating a user."""
        user = User(phone="+919876543210", name="Test User")
        test_db_session.add(user)
        await test_db_session.commit()
        
        assert user.id is not None
        assert user.phone == "+919876543210"
        assert user.name == "Test User"
        assert user.created_at is not None

    @pytest.mark.asyncio
    async def test_user_unique_phone(self, test_db_session):
        """Test that phone numbers must be unique."""
        user1 = User(phone="+919876543210", name="User 1")
        test_db_session.add(user1)
        await test_db_session.commit()
        
        user2 = User(phone="+919876543210", name="User 2")
        test_db_session.add(user2)
        
        with pytest.raises(Exception):  # IntegrityError
            await test_db_session.commit()

    @pytest.mark.asyncio
    async def test_query_user_by_phone(self, test_db_session):
        """Test querying user by phone number."""
        user = User(phone="+919876543210", name="Test User")
        test_db_session.add(user)
        await test_db_session.commit()
        
        result = await test_db_session.execute(
            select(User).where(User.phone == "+919876543210")
        )
        found_user = result.scalar_one_or_none()
        
        assert found_user is not None
        assert found_user.phone == "+919876543210"


@pytest.mark.integration
@pytest.mark.database
class TestConversationModel:
    """Test Conversation model database operations."""

    @pytest.mark.asyncio
    async def test_create_conversation(self, test_db_session):
        """Test creating a conversation."""
        user = User(phone="+919876543210", name="Test User")
        test_db_session.add(user)
        await test_db_session.commit()
        
        conversation = Conversation(
            user_id=user.id,
            channel=ChannelType.WHATSAPP,
        )
        test_db_session.add(conversation)
        await test_db_session.commit()
        
        assert conversation.id is not None
        assert conversation.user_id == user.id
        assert conversation.channel == ChannelType.WHATSAPP
        assert conversation.started_at is not None

    @pytest.mark.asyncio
    async def test_conversation_user_relationship(self, test_db_session):
        """Test conversation-user relationship."""
        user = User(phone="+919876543210", name="Test User")
        test_db_session.add(user)
        await test_db_session.commit()
        
        conversation = Conversation(
            user_id=user.id,
            channel=ChannelType.WHATSAPP,
        )
        test_db_session.add(conversation)
        await test_db_session.commit()
        
        # Refresh to load relationships
        await test_db_session.refresh(conversation, ["user"])
        
        assert conversation.user is not None
        assert conversation.user.phone == "+919876543210"


@pytest.mark.integration
@pytest.mark.database
class TestMessageModel:
    """Test Message model database operations."""

    @pytest.mark.asyncio
    async def test_create_message(self, test_db_session):
        """Test creating a message."""
        user = User(phone="+919876543210", name="Test User")
        test_db_session.add(user)
        await test_db_session.commit()
        
        conversation = Conversation(
            user_id=user.id,
            channel=ChannelType.WHATSAPP,
        )
        test_db_session.add(conversation)
        await test_db_session.commit()
        
        message = Message(
            conversation_id=conversation.id,
            role=MessageRole.USER,
            content="Hello, I need help",
        )
        test_db_session.add(message)
        await test_db_session.commit()
        
        assert message.id is not None
        assert message.conversation_id == conversation.id
        assert message.role == MessageRole.USER
        assert message.content == "Hello, I need help"
        assert message.created_at is not None

    @pytest.mark.asyncio
    async def test_message_conversation_relationship(self, test_db_session):
        """Test message-conversation relationship."""
        user = User(phone="+919876543210", name="Test User")
        test_db_session.add(user)
        await test_db_session.commit()
        
        conversation = Conversation(
            user_id=user.id,
            channel=ChannelType.WHATSAPP,
        )
        test_db_session.add(conversation)
        await test_db_session.commit()
        
        message = Message(
            conversation_id=conversation.id,
            role=MessageRole.USER,
            content="Test message",
        )
        test_db_session.add(message)
        await test_db_session.commit()
        
        # Refresh to load relationships
        await test_db_session.refresh(message, ["conversation"])
        
        assert message.conversation is not None
        assert message.conversation.id == conversation.id

    @pytest.mark.asyncio
    async def test_conversation_messages_relationship(self, test_db_session):
        """Test conversation can access its messages."""
        user = User(phone="+919876543210", name="Test User")
        test_db_session.add(user)
        await test_db_session.commit()
        
        conversation = Conversation(
            user_id=user.id,
            channel=ChannelType.WHATSAPP,
        )
        test_db_session.add(conversation)
        await test_db_session.commit()
        
        message1 = Message(
            conversation_id=conversation.id,
            role=MessageRole.USER,
            content="First message",
        )
        message2 = Message(
            conversation_id=conversation.id,
            role=MessageRole.ASSISTANT,
            content="Second message",
        )
        test_db_session.add_all([message1, message2])
        await test_db_session.commit()
        
        # Refresh to load relationships
        await test_db_session.refresh(conversation, ["messages"])
        
        assert len(conversation.messages) == 2
        assert conversation.messages[0].content == "First message"
        assert conversation.messages[1].content == "Second message"

# Made with Bob
