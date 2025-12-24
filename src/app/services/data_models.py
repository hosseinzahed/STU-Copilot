from datetime import datetime, timezone
from typing import Optional
import chainlit as cl
from dataclasses import dataclass


class ChatMessage:
    def __init__(self, message: cl.Message, user_id: str):
        self.id = message.id  # Unique identifier for Cosmos DB
        self.thread_id = message.thread_id  # Thread identifier
        self.user_id = user_id  # User identifier
        self.message = message.content  # Message content
        self.timestamp = datetime.now(
            timezone.utc).isoformat()  # ISO 8601 format
        self.role = message.author  # 'user' or 'assistant'
        self.type = "message"  # Type of the object, can be 'message' or 'thread'

    def to_dict(self):
        return {
            "id": self.id,
            "thread_id": self.thread_id,
            "user_id": self.user_id,
            "message": self.message,
            "timestamp": self.timestamp,
            "role": self.role,
            "type": self.type
        }

    @staticmethod
    def from_dict(data: dict):
        return ChatMessage(
            id=data.get("id"),
            user_id=data.get("user_id"),
            thread_id=data.get("thread_id"),
            message=data.get("message"),
            timestamp=data.get("timestamp"),
            role=data.get("role", "user"),
            type=data.get("type", "message"))


class ChatThread:
    def __init__(self,
                 thread_id: str,
                 user_id: str,
                 title: str = None,
                 user_job_title: Optional[str] = None,
                 created_at: Optional[str] = None
                 ):
        self.id = thread_id  # Unique thread identifier
        self.user_id = user_id  # User identifier
        self.title = title  # Optional thread title
        self.user_job_title = user_job_title  # Optional user job title
        self.messages = []  # List of ChatMessage objects
        self.created_at = created_at or datetime.now(timezone.utc).isoformat()
        self.type = "thread"

    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "title": self.title,
            "user_job_title": self.user_job_title,
            "messages": [msg.to_dict() for msg in self.messages],
            "created_at": self.created_at,
            "type": self.type
        }

    @staticmethod
    def from_dict(data: dict):
        messages = [ChatMessage.from_dict(msg)
                    for msg in data.get("messages", [])]
        return ChatThread(
            id=data.get("id"),
            user_id=data.get("user_id"),
            title=data.get("title"),
            user_job_title=data.get("user_job_title"),
            messages=messages,
            created_at=data.get("created_at"),
            type=data.get("type", "thread"))


@dataclass
class PreprocessOutput:
    """Data class to hold the output of the preprocess executor."""
    messages: list[ChatMessage]
    task_list: cl.TaskList


@dataclass
class KnowledgeBaseOutput:
    """Data class to hold the output of the knowledge base retrieval executor."""
    answer: str
    task_list: cl.TaskList


@dataclass
class MSDocsOutput:
    """Data class to hold the output of the Microsoft Docs search executor."""
    answer: str
    task_list: cl.TaskList

@dataclass
class AggregateOutput:
    """Data class to hold the output of the aggregate results executor."""
    aggregated_response: str
    task_list: cl.TaskList