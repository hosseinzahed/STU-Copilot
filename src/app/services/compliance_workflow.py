import os
import aiohttp
import requests
from typing import Dict, Any
from agent_framework import (
    ChatAgent,
    ChatMessage,
    Workflow,
    WorkflowBuilder,
    WorkflowContext,
    MCPStreamableHTTPTool,
    executor
)
from agent_framework.azure import AzureOpenAIChatClient
from urllib.parse import quote



# Load environment variables for Foundry
foundry_endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
foundry_api_key = os.getenv("AI_FOUNDRY_KEY")
foundry_project_endpoint = os.getenv(
    "AI_FOUNDRY_PROJECT_ENDPOINT")
foundry_api_version = os.getenv(
    "AI_FOUNDRY_API_VERSION", "2024-12-01-preview")

# Load environment variables for AI Search
ai_search_endpoint = os.getenv("AI_SEARCH_ENDPOINT")
ai_search_api_key = os.getenv("AI_SEARCH_KEY")
ai_search_knowledge_base_name = os.getenv(
    "KNOWLEDGE_BASE_NAME", "stu-copilot-kb")

# Initialize the Azure OpenAI Chat Client
chat_client = AzureOpenAIChatClient(
    endpoint=foundry_endpoint,
    api_key=foundry_api_key,
    deployment_name="gpt-5.2-chat"
)


def get_compliance_workflow() -> Workflow:
    """Creates and returns a compliance workflow.
    Returns:
        Workflow: A workflow object for compliance tasks.        
    """
    # Define the compliance workflow
    compliance_workflow = (
        WorkflowBuilder(
            name="Compliance Workflow",
            description="A workflow for handling compliance-related tasks.",
            max_iterations=1
        )
        .set_start_executor(knowledge_base_retrieval_executor)
        .build()
    )

    return compliance_workflow


@executor(id="knowledge_base_retrieval_executor")
async def knowledge_base_retrieval_executor(messages: list[ChatMessage], ctx: WorkflowContext[str]) -> Dict[str, Any]:
    """Executor to retrieve information from the compliance knowledge base.
    Args:
        query (str): The query string to search in the knowledge base.

    Returns:
        str: The retrieved information from the knowledge base.
    """
    # Retrieve from the knowledge base
    json_response = await _retrieve_knowledge(messages[-1].text)

    # Process the response
    processed_md_response = _process_kb_response(json_response)

    # Return the processed Markdown response
    return await ctx.yield_output(processed_md_response)


async def _retrieve_knowledge(query: str) -> str:
    """Helper method to retrieve knowledge from the knowledge base.
    Args:
        query (str): The query string to search in the knowledge base.
    Returns:
        str: The retrieved information from the knowledge base.
    """
    # Prepare the url for knowledge base retrieval
    kb_retrieval_url = f"{ai_search_endpoint}/knowledgebases/{ai_search_knowledge_base_name}/retrieve?api-version=2025-11-01-preview"

    # Prepare headers and payload for the request
    headers = {
        "api-key": ai_search_api_key,
        "Content-Type": "application/json"
    }

    # Prepare the payload for the request
    payload = {
        "messages": [
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": query
                    }
                ]
            }
        ],
        "outputMode": "answerSynthesis",
        "includeActivity": False,
        "maxRuntimeInSeconds": 120,        
        #"maxOutputSize": 6000
    }

    # Make the POST request to retrieve information
    timeout = aiohttp.ClientTimeout(total=120)  # 120 seconds (2 minutes)    
    async with aiohttp.ClientSession(timeout=timeout) as session:
        async with session.post(url=kb_retrieval_url,
                                headers=headers,
                                json=payload
                                ) as response:
            response.raise_for_status()
            return await response.json()


def _process_kb_response(response_json: str) -> str:
    """Helper method to process the knowledge base response.
    Args:
        response_json (str): The JSON response from the knowledge base. 
    Returns:
        str: The processed answer from the knowledge base response.
    """
    # Extract the main response text
    response_text = response_json["response"][0]["content"][0]["text"]
    print("Response Text:", response_text)
    
    # Extract unique reference titles    
    references_list = "\n".join(
        f"{ref['id']}. [{ref['title']}]({quote(ref['title'])}) - (Page #{_extract_page(ref["docKey"])})" 
        for ref in sorted(response_json.get("references", []), key=lambda x: int(x['id']))
    )    
    print("References List:", references_list)
    
    # Combine response text with references
    processed_answer = f"{response_text}\n\n### References:\n{references_list}"

    return processed_answer

def _extract_page(doc_key: str) -> str:
    # Extract the page number or relevant information from the docKey
    # Assuming the docKey format contains the page number after a specific delimiter, e.g., "page_"
    if "_pages_" in doc_key:
        return doc_key.split("_pages_")[-1]
    return "Undefined"

# def _get_intents_extractor_agent(self) -> ChatAgent:


# agent = ChatAgent(
#     chat_client=self.chat_client,
#     description="Compliance Intent Extraction Agent",
#     instructions="""
#         Tell me a joke about compliance and regulations.
#     """,
#     model_id="gpt-4.1-mini"
# )
# return agent


# async def retrieve_from_knowledge_base(self, query: str, knowledge_sources: list = None) -> Dict[str, Any]:
# ai_search_endpoint = os.getenv("AI_SEARCH_ENDPOINT")
# ai_search_key = os.getenv("AI_SEARCH_KEY")
# knowledge_base_name = "stu-copilot-kb"

# # AI Search Context Provider
# # Create the MCP tool
# mcp_server = MCPStreamableHTTPTool(
#     name="AI Search MCP Tool",
#     description="Tool to retrieve information from the compliance knowledge base using AI Search.",
#     url=f"{ai_search_endpoint}/knowledgebases/{knowledge_base_name}/mcp?api-version=2025-11-01-preview",
#     headers={
#         "api-key": f"{ai_search_key}",
#         "Content-Type": "application/json"
#     },
#     approval_mode="never_require",
#     allowed_tools=["knowledge_base_retrieve"],
#     load_prompts=False,
#     load_tools=True,
#     request_timeout=60,
#     timeout=60
# )

# # Connect and load tools
# await mcp_server.connect()
# await mcp_server.load_tools()

# # Call the tool with the query
# results = await mcp_server.call_tool(
#     "knowledge_base_retrieve",
#     request={
#         "knowledgeAgentIntents": [
#             query
#         ]
#     }
# )

# # Close the MCP server connection
# await mcp_server.close()

# return results


# # Global instance
# compliance_service = ComplianceService()

#     from agent_framework import ChatAgent
# from agent_framework.azure import AzureAIAgentClient, AzureAISearchContextProvider
# from azure.identity.aio import DefaultAzureCredential
# search_provider = AzureAISearchContextProvider(
#    endpoint="https://myservice.search.windows.net",
#    index_name="my-index",
#    api_key="YOUR_SEARCH_KEY", # or use DefaultAzureCredential
#    mode="semantic",
#    top_k=3
# )
# async with AzureAIAgentClient(
#    credential=DefaultAzureCredential(),
#    project_endpoint="YOUR_PROJECT_ENDPOINT",
#    model_deployment_name="gpt-4o"
# ) as client:
#    async with ChatAgent(chat_client=client, context_providers=search_provider) as agent:
#        response = await agent.run("What information is in the knowledge base?")
#        print(response.text)

# search_provider = AzureAISearchContextProvider(
#    endpoint="https://myservice.search.windows.net",
#    index_name="my-index",
#    api_key="YOUR_SEARCH_KEY",
#    mode="agentic",
#    knowledge_base_name="my-knowledge-base",
#    azure_openai_resource_url="https://myopenai.openai.azure.com",
#    top_k=5
# )
# async with ChatAgent(
#    chat_client=client,
#    model=model_deployment,
#    context_providers=search_provider
# ) as agent:
#    response = await agent.run("Analyze and compare topics across documents")
#    print(response.text)
