import os
from typing import List, Dict, Optional
import chainlit as cl
from services.chat_service import chat_service
from services.agent_factory import agent_factory
from agent_framework import ChatAgent, ChatMessage, AgentThread
import logging
import socketio
from engineio.payload import Payload
from chainlit.types import ThreadDict


# Set the buffer size to 10MB or use a configurable value from the environment
MAX_HTTP_BUFFER_SIZE = int(os.getenv("MAX_HTTP_BUFFER_SIZE", 100_000_000))
# Configurable buffer size
sio = socketio.AsyncServer(
    async_mode='aiohttp',
    transport='websocket',
    max_http_buffer_size=MAX_HTTP_BUFFER_SIZE)
Payload.max_decode_packets = 500


# Basic logging configuration
logging.basicConfig(level=logging.CRITICAL)
logging.getLogger("azure").setLevel(logging.CRITICAL)
logging.getLogger("httpx").setLevel(logging.ERROR)
logging.getLogger("azure.cosmos").setLevel(logging.CRITICAL)
logging.getLogger("openai").setLevel(logging.ERROR)
logging.getLogger("semantic_kernel").setLevel(logging.INFO)
logging.getLogger("asyncio").setLevel(logging.CRITICAL)
logging.getLogger("httpcore").setLevel(logging.CRITICAL)
logging.getLogger("anyio").setLevel(logging.CRITICAL)
logging.getLogger("aiohttp").setLevel(logging.CRITICAL)
logging.getLogger("aiohttp.access").setLevel(logging.CRITICAL)
logging.getLogger("engineio").setLevel(logging.CRITICAL)
logging.getLogger("socketio").setLevel(logging.CRITICAL)
logger = logging.getLogger(__name__)

# Initialize services and agents
agents: dict[str, ChatAgent] = agent_factory.get_agents()


@cl.oauth_callback
async def oauth_callback(
    provider_id: str,
    token: str,
    raw_user_data: Dict[str, str],
    default_user: cl.User,
) -> Optional[cl.User]:
    print(f"OAuth callback for provider {provider_id}")
    default_user.identifier = raw_user_data["mail"]
    default_user.display_name = raw_user_data["displayName"]
    default_user.metadata["user_id"] = raw_user_data["id"]
    default_user.metadata["first_name"] = raw_user_data["givenName"]
    default_user.metadata["job_title"] = raw_user_data["jobTitle"]
    default_user.metadata["office_location"] = raw_user_data["officeLocation"]
    return default_user


@cl.on_chat_start
async def on_chat_start():

    # Get user info
    user = cl.user_session.get("user")

    # Populate commands in the user session
    await cl.context.emitter.set_commands(
        chat_service.get_commands()
    )

    # Initialize the chat service and chat history
    chat_history: list[ChatMessage] = []

    # Construct the welcome message
    welcome_message = chat_service.get_welcome_message(
        user_first_name=user.metadata.get(
            "first_name", "Guest") if user else "Guest",
        user_job_title=user.metadata.get(
            "job_title", None) if user else None,
    )

    # Clear the latest agent name
    latest_agent_name = None

    # Show the welcome message to the user
    await cl.Message(content=welcome_message).send()

    # chat_history.append(ChatMessage(role="assistant", content=welcome_message))

    cl.user_session.set("chat_history", chat_history)
    cl.user_session.set("chat_thread", None)
    cl.user_session.set("latest_agent_name", latest_agent_name)


@cl.on_message
async def on_message(user_message: cl.Message):

    chat_history: list[ChatMessage] = cl.user_session.get("chat_history")
    chat_thread: AgentThread = cl.user_session.get("chat_thread")

    responder_agent: ChatAgent = chat_service.select_responder_agent(
        agents=agents,
        current_message=user_message,
        latest_agent_name=cl.user_session.get("latest_agent_name")
    )

    print(f"Selected responder agent: {responder_agent.name}")

    agent_actions = chat_service.get_actions(
        agent_name=responder_agent.name)

    # Set the latest agent in the user session
    cl.user_session.set("latest_agent_name", responder_agent.name)

    chat_history.append(ChatMessage(role="user", content=user_message.content))
    answer = cl.Message(content="", actions=agent_actions)

    # Select which messages to send to the agent
    messages = chat_history if responder_agent.name in [
        "orchestrator_agent",
        "questioner_agent",
        "planner_agent"
    ] else user_message.content

    # Set the latest agent in the user session
    cl.user_session.set("latest_agent", responder_agent.name)

    # Stream the agent's response token by token
    async for token in responder_agent.run_stream(
            messages=messages,
            #thread=chat_thread
    ):
        if token.text:
            await answer.stream_token(token.text)

    cl.user_session.set("chat_thread", chat_thread)
    chat_history.append(ChatMessage(role="assistant", content=answer.content))

    # Send the final message
    await answer.send()


@cl.on_chat_resume
async def on_chat_resume(thread: ThreadDict):

    await cl.context.emitter.set_commands(
        chat_service.get_commands()
    )
    chat_history: list[ChatMessage] = []

    for step in thread["steps"]:
        if step["type"] == "assistant_message":
            chat_history.append(ChatMessage(
                role="assistant", content=step["output"]))
        elif step["type"] == "user_message":
            chat_history.append(ChatMessage(
                role="user", content=step["output"]))
    cl.user_session.set("chat_history", chat_history)

    chat_thread = AgentThread(service_thread_id=thread["id"])

    cl.user_session.set("chat_thread", chat_thread)


@cl.set_starters  # type: ignore
async def set_starts() -> List[cl.Starter]:
    return [
        cl.Starter(
            label="AI Assistant",
            message="Design an AI assistant with frontend, backend, and database integration.",
        ),
        cl.Starter(
            label="Data Analysis Bot",
            message="Create a bot to analyze and visualize data trends.",
        ),
        cl.Starter(
            label="Weather Bot",
            message="How is the weather today?",
        ),
    ]


@cl.action_callback("action_button")
async def on_action_button(action: cl.Action):
    """Handle action button clicks."""

    chat_history: list[ChatMessage] = cl.user_session.get("chat_history")
    user_prompts = "\n".join(
        [msg.content for msg in chat_history if msg.role == "user"]
    )

    await on_message(cl.Message(
        content=user_prompts,
        command=action.payload["command"]
    ))
