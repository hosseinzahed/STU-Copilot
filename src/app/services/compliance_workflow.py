import os
import re
import aiohttp
from typing import Any, Never
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
import chainlit as cl
from dataclasses import dataclass


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
ai_search_api_version = os.getenv(
    "AI_SEARCH_API_VERSION", "2025-11-01-preview")
ai_search_knowledge_base_name = os.getenv(
    "KNOWLEDGE_BASE_NAME", "stu-copilot-kb")

# Load environment variable for storage account
storage_account_name = os.getenv("APP_AZURE_STORAGE_ACCOUNT")

# Initialize the Azure OpenAI Chat Client
chat_client = AzureOpenAIChatClient(
    endpoint=foundry_endpoint,
    api_key=foundry_api_key,
    deployment_name="gpt-5.2-chat"
)

# Define tasks
analyze_query_task = cl.Task(
    title="Analyzing the query",
    status=cl.TaskStatus.READY,
    forId="analyze_query_task"
)
retrieve_kb_task = cl.Task(
    title="Searching the knowledge base",
    status=cl.TaskStatus.READY,
    forId="retrieve_kb_task"
)
ms_docs_search_task = cl.Task(
    title="Searching Microsoft Docs",
    status=cl.TaskStatus.READY,
    forId="ms_docs_search_task"
)
aggregate_results_task = cl.Task(
    title="Aggregating results",
    status=cl.TaskStatus.READY,
    forId="aggregate_results_task"
)


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
            # max_iterations=1
        )
        .set_start_executor(preprocess_query)
        .add_fan_out_edges(preprocess_query, [retrieve_knowledge_base, search_ms_docs])
        .add_fan_in_edges([retrieve_knowledge_base, search_ms_docs], aggregate_results)
        .build()
    )

    return compliance_workflow


@executor(id="preprocess_query")
async def preprocess_query(messages: list[ChatMessage],
                           ctx: WorkflowContext[PreprocessOutput]) -> None:
    """Executor to preprocess the input messages.
    Args:
        messages (list[ChatMessage]): The list of chat messages.
        chat_thread (AgentThread): The current chat thread.
    Returns:
        PreprocessOutput: The preprocessed output containing messages, chat thread, and task list.
    """

    # Create a new task list
    task_list = cl.TaskList(
        name="compliance_workflow_tasks",
        title="Compliance Workflow Tasks",
        status="⌛ Running…",
        tasks=[
            analyze_query_task,
            retrieve_kb_task,
            ms_docs_search_task,
            aggregate_results_task
        ]               
    )

    # Prepare the output
    output = PreprocessOutput(
        messages=messages,
        task_list=task_list
    )

    # Update the analyze query task status
    analyze_query_task.status = cl.TaskStatus.DONE
    await task_list.update()

    # Send the output to the next executor
    return await ctx.send_message(output)


@executor(id="retrieve_knowledge_base")
async def retrieve_knowledge_base(input: PreprocessOutput,
                                  ctx: WorkflowContext[KnowledgeBaseOutput, Never]):
    """Executor to retrieve information from the compliance knowledge base.
    Args:
        query (str): The query string to search in the knowledge base.

    Returns:
        str: The retrieved information from the knowledge base.
    """

    # Update the task status
    retrieve_kb_task.status = cl.TaskStatus.RUNNING
    await input.task_list.update()

    # Call the helper method to retrieve knowledge
    json_response = await _retrieve_knowledge(input.messages[-1].text)

    # Process the response
    processed_md_response = _process_kb_response(json_response)

    # Prepare the output
    output = KnowledgeBaseOutput(
        answer=processed_md_response,
        task_list=input.task_list
    )

    # Update the task status
    retrieve_kb_task.status = cl.TaskStatus.DONE
    await input.task_list.update()

    # Return the output to the next executor
    return await ctx.send_message(output)


@executor(id="search_ms_docs")
async def search_ms_docs(input: PreprocessOutput, ctx: WorkflowContext[MSDocsOutput, Never]):
    """Executor to search Microsoft Docs for additional information.
    Args:
        query (str): The query string to search in Microsoft Docs.
    Returns:
        str: The retrieved information from Microsoft Docs.
    """
    # Update the task status
    ms_docs_search_task.status = cl.TaskStatus.RUNNING
    await input.task_list.update()

    # Create the MCP tool
    mcp_server = MCPStreamableHTTPTool(
        name="Microsoft Docs MCP Tool",
        url="https://learn.microsoft.com/api/mcp"
    )

    # Create the agent
    microsoft_docs_agent = ChatAgent(
        chat_client=AzureOpenAIChatClient(
            endpoint=foundry_endpoint,
            api_key=foundry_api_key,
            deployment_name="gpt-5.2-chat"
        ),
        name="microsoft_docs_agent",
        description="Microsoft Docs agent that searches for relevant Microsoft documentation.",
        instructions="""
                You provide information from Microsoft Docs using the search tool.
                - Rephrase queries max into up to 3 parallel searches for better results
                - Cite sources with links and include all images from search results
                - Format responses in markdown with related topic suggestions
            """,
        tools=[mcp_server],
        allow_multiple_tool_calls=True
    )

    # Run the agent with the query
    response = await microsoft_docs_agent.run(input.messages[-1].text)

    # Prepare the output
    output = MSDocsOutput(
        answer=response.text,
        task_list=input.task_list
    )

    # Update the task status
    ms_docs_search_task.status = cl.TaskStatus.DONE
    await input.task_list.update()

    # Return a placeholder response
    return await ctx.send_message(output)


@executor(id="aggregate_results")
async def aggregate_results(results: list[Any],
                            ctx: WorkflowContext[Never, str]):
    """Executor to aggregate results from knowledge base and Microsoft Docs search.
    Args:
        kb_output (KnowledgeBaseOutput): The output from the knowledge base retrieval executor.
        ms_docs_output (MSDocsOutput): The output from the Microsoft Docs search executor.
    Returns:
        str: The aggregated response.    
    """
    # Initialize outputs
    kb_output = None
    ms_docs_output = None

    # Extract outputs from results
    for result in results:
        if isinstance(result, KnowledgeBaseOutput):
            kb_output = result
        elif isinstance(result, MSDocsOutput):
            ms_docs_output = result

    # Update the task status
    aggregate_results_task.status = cl.TaskStatus.RUNNING
    await kb_output.task_list.update()

    # Aggregate the results
    final_output = f"> ## 📃 Knowledge Base Results: \n{kb_output.answer}\n --- \n> ## 📚 Microsoft Docs Results: \n{ms_docs_output.answer}"

    # Update the task list status to completed
    aggregate_results_task.status = cl.TaskStatus.DONE
    kb_output.task_list.status = "✅ Completed"
    await kb_output.task_list.update()
    await kb_output.task_list.remove()

    # Return the final aggregated output
    return await ctx.yield_output(final_output)


async def _retrieve_knowledge(query: str) -> str:
    """Helper method to retrieve knowledge from the knowledge base.
    Args:
        query (str): The query string to search in the knowledge base.
    Returns:
        str: The retrieved information from the knowledge base.
    """
    # Prepare the query
    query += "\n**Format responses in Markdown with proper headers no bigger than `###`. Use an official tone.**"

    # print("Knowledge Base Query:", query)

    # Prepare the url for knowledge base retrieval
    kb_retrieval_url = f"{ai_search_endpoint}/knowledgebases/{ai_search_knowledge_base_name}/retrieve?api-version={ai_search_api_version}"

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
        # "maxOutputSize": 6000
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
    refined_response_text = re.sub(
        r'\[ref_id:(\d+)\]', r' *[ref:\1]* ', response_text)
    # print("Response Text:", refined_response_text)

    # Extract unique reference titles
    references_list = "\n".join(
        f"{ref['id']}. [{ref['title']}]({quote(ref['title'])}) - (Page #{_extract_page(ref["docKey"])})"
        for ref in sorted(response_json.get("references", []), key=lambda x: int(x['id']))
    )
    # print("References List:", references_list)

    # Combine response text with references
    processed_answer = f"{refined_response_text}\n\n### References:\n{references_list}"

    return processed_answer


def _extract_page(doc_key: str) -> str:
    # Extract the page number or relevant information from the docKey
    # Assuming the docKey format contains the page number after a specific delimiter, e.g., "page_"
    if "_pages_" in doc_key:
        return doc_key.split("_pages_")[-1]
    return "Undefined"
