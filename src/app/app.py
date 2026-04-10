import os
from typing import List, Dict, Optional
import chainlit as cl
from services.chat_service import chat_service
from services.agent_factory import agent_factory
from agent_framework import Agent, Message, AgentSession
from agent_framework.observability import configure_otel_providers
import logging
import socketio
from engineio.payload import Payload
from chainlit.types import ThreadDict
from utils import check_env_vars, extract_image_elements

# Check for required environment variables
check_env_vars()

# Configure OpenTelemetry providers
configure_otel_providers()

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
agents: dict[str, Agent] = agent_factory.get_agents()


@cl.oauth_callback
async def oauth_callback(
    provider_id: str,
    token: str,
    raw_user_data: Dict[str, str],
    default_user: cl.User,
) -> Optional[cl.User]:
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
    chat_history: list[Message] = []

    # Clear the latest agent name
    last_used_agent_name = None

    # Store in user session
    cl.user_session.set("chat_history", chat_history)

    # Initialize empty chat thread
    cl.user_session.set("chat_session", None)

    # Store latest agent name
    cl.user_session.set("last_used_agent_name", last_used_agent_name)


@cl.on_message
async def on_message(user_message: cl.Message):

    # Retrieve chat history and thread from user session
    chat_history: list[Message] = cl.user_session.get("chat_history")

    # Select the appropriate responder agent
    responder_agent: Agent = chat_service.select_responder_agent(
        agents=agents,
        current_message=user_message,
        last_used_agent_name=cl.user_session.get("last_used_agent_name")
    )
    print(f"Selected responder agent: {responder_agent.name}")

    # Get chat session from user session or create a new one if it doesn't exist
    chat_session: AgentSession = cl.user_session.get("chat_session")
    if not chat_session:
        # Create a new chat session for the agent
        chat_session = responder_agent.create_session()
        print(f"Created new chat session with ID: {chat_session.session_id}")

    # Set the latest agent in the user session
    cl.user_session.set("last_used_agent_name", responder_agent.name)

    # Append user message to chat history
    chat_history.append(Message(role="user", contents=user_message.content))
    answer = cl.Message(content="")

    # Set the latest agent in the user session
    cl.user_session.set("latest_agent", responder_agent.name)

    # Stream the agent's response token by token
    async for chunk in responder_agent.run(
            messages=chat_history,
            session=chat_session,
            stream=True
    ):
        # Append token to the answer content
        if chunk.text:
            await answer.stream_token(chunk.text)

    # Update chat history and thread
    cl.user_session.set("chat_session", chat_session)
    chat_history.append(Message(role="assistant", contents=answer.content))

    # Check for image URLs in the response and display them
    image_elements = extract_image_elements(answer.content)
    if image_elements:
        answer.elements = image_elements

    # Send the final message
    await answer.send()


@cl.on_chat_resume
async def on_chat_resume(thread: ThreadDict):

    # Populate commands in the user session
    await cl.context.emitter.set_commands(
        chat_service.get_commands()
    )

    # Reconstruct chat history from the thread steps
    chat_history: list[Message] = []

    # Rebuild chat history
    for step in thread["steps"]:
        if step["type"] == "assistant_message":
            chat_history.append(Message(
                role="assistant", contents=step["output"]))
        elif step["type"] == "user_message":
            chat_history.append(Message(
                role="user", contents=step["output"]))

    # Store chat history in user session
    cl.user_session.set("chat_history", chat_history)

    # Reconstruct the AgentSession from the thread ID
    chat_session = AgentSession(session_id=thread["id"])

    # Store chat thread in user session
    cl.user_session.set("chat_session", chat_session)


@cl.set_starters  # type: ignore
async def set_starts() -> List[cl.Starter]:
    return [
        cl.Starter(
            label="GPT-5.2 Model Availability",
            message="In which regions is the GPT-5 model available?",
        ),
        cl.Starter(
            label="AI Landing Zone",
            message="Provide an overview of AI Landing Zone best practices.",
        ),
        cl.Starter(
            label="Agent Framework",
            message="Explain the key components of the Agent Framework.",
        ),
    ]


@cl.action_callback("action_button")
async def on_action_button(action: cl.Action):
    """Handle action button clicks."""

    # Retrieve chat history from user session
    chat_history: list[Message] = cl.user_session.get("chat_history")

    # Combine all user messages into a single prompt
    user_prompts = "\n".join(
        [msg.text for msg in chat_history if msg.role == "user"]
    )

    # Send a new message with the combined prompts and command
    await on_message(cl.Message(
        content=user_prompts,
        command=action.payload["command"]
    ))
