import chainlit as cl
from chainlit.types import CommandDict
from agent_framework import ChatAgent
from .agent_factory import agent_factory


class ChatService:
    """Service for managing chat agents and plugins."""

    def __init__(self):
        """Initialize the chat service."""
        agents = agent_factory.get_agents()
        self.agents_dict = {
            "microsoft_docs_agent": {
                "title": "Microsoft Docs",
                "description": "Search Microsoft documentation",
                "icon": "file-search",
                "is_button": False,
                "is_persistent": True,
                "is_command": True,
                "is_action": True,
                "command": "Microsoft Docs",
                "action_name": "action_button",
                "agent_object": agents.get("microsoft_docs_agent")
            },
            "github_docs_search_agent": {
                "title": "GitHub Docs",
                "description": "Search GitHub documentation",
                "icon": "file-search",
                "is_button": False,
                "is_persistent": True,
                "is_command": True,
                "is_action": True,
                "command": "GitHub Docs",
                "action_name": "action_button",
                "agent_object": agents.get("github_docs_search_agent")
            },
            "github_agent": {
                "title": "GitHub",
                "description": "Search for GitHub repositories",
                "icon": "github",
                "is_button": False,
                "is_persistent": True,
                "is_command": True,
                "is_action": True,
                "command": "GitHub",
                "action_name": "action_button",
                "agent_object": agents.get("github_agent")
            },
            "seismic_agent": {
                "title": "Seismic Presentations",
                "description": "Search for Seismic content",
                "icon": "presentation",
                "is_button": False,
                "is_persistent": True,
                "is_command": True,
                "is_action": True,
                "command": "Seismic Presentations",
                "action_name": "action_button",
                "agent_object": agents.get("seismic_agent")
            },
            "blog_posts_agent": {
                "title": "Blog Posts",
                "description": "Search for blog posts",
                "icon": "rss",
                "is_button": False,
                "is_persistent": False,
                "is_command": True,
                "is_action": True,
                "command": "Blog Posts",
                "action_name": "action_button",
                "agent_object": agents.get("blog_posts_agent")
            },
            "bing_search_agent": {
                "title": "Bing Search",
                "description": "Search the web using Bing",
                "icon": "search",
                "is_button": False,
                "is_persistent": False,
                "is_command": True,
                "is_action": True,
                "command": "Bing Search",
                "action_name": "action_button",
                "agent_object": agents.get("bing_search_agent")
            },
            "aws_docs_agent": {
                "title": "AWS Documentation",
                "description": "Search AWS documentation",
                "icon": "file-search",
                "is_button": False,
                "is_persistent": False,
                "is_command": True,
                "is_action": True,
                "command": "AWS Documentation",
                "action_name": "action_button",
                "agent_object": agents.get("aws_docs_agent")
            }            
        }    

    def get_commands(self) -> list[CommandDict]:
        """Return the list of available commands."""

        commands = []
        for agent in self.agents_dict.values():
            # Only include agents that are marked as commands
            if agent["is_command"]:
                commands.append({
                    "id": agent["title"],
                    "description": agent["description"],
                    "icon": agent["icon"],
                    "button": agent["is_button"],
                    "persistent": agent["is_persistent"]                    
                })
        return commands    

    def select_responder_agent(self,
                               agents: dict[str, ChatAgent],
                               current_message: cl.Message,
                               latest_agent_name: str) -> ChatAgent:
        """Select the appropriate agent based on the current message and chat history."""

        print(f"Current message command: {current_message.command}")
        print(f"Latest agent in use: {latest_agent_name}")

        # If the current message is a command, use the corresponding agent
        if current_message.command:
            # Select the agent based on the command from self.agents_dict
            for agent in self.agents_dict.values():
                if agent["is_action"] and agent["command"] == current_message.command:
                    selected_agent: ChatAgent = agent["agent_object"]
                    print(
                        f"Selected agent for command '{current_message.command}': {selected_agent.name}")
                    return selected_agent

        # If the current message is not a command, determine the agent based on the chat history
        elif latest_agent_name is None:
            return agents.get("orchestrator_agent")
        else:
            return agents.get(latest_agent_name)


# Global instance
chat_service = ChatService()
