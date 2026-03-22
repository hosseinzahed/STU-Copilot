import os
import re
import aiohttp
from typing import Any, Never
from agent_framework import (
    Agent,
    Message,
    Workflow,
    WorkflowBuilder,
    WorkflowContext,
    MCPStreamableHTTPTool,
    executor)
from agent_framework.azure import AzureOpenAIResponsesClient, AzureAISearchContextProvider
from azure.search.documents import SearchClient
from urllib.parse import quote
from azure.identity import DefaultAzureCredential
import chainlit as cl
from .data_models import PreprocessOutput, KnowledgeBaseOutput, MSDocsOutput, AggregateOutput
from .storage_account_service import storage_account_service

# Load environment variables for AI Search
ai_search_endpoint = os.getenv("AI_SEARCH_ENDPOINT")
ai_search_api_key = os.getenv("AI_SEARCH_KEY")
ai_search_api_version = os.getenv(
    "AI_SEARCH_API_VERSION", "2025-11-01-preview")
ai_search_knowledge_base_name = os.getenv(
    "KNOWLEDGE_BASE_NAME", "kb-compliance-general")

# Load environment variable for storage account
storage_account_name = os.getenv("APP_AZURE_STORAGE_ACCOUNT")
compliance_container_name = "compliance-docs"

# Credential
credential = DefaultAzureCredential()

# Initialize the Azure OpenAI Chat Client
foundry_client = AzureOpenAIResponsesClient(
    project_endpoint=os.getenv("AI_FOUNDRY_PROJECT_ENDPOINT"),
    credential=credential,
    deployment_name="gpt-5.2-chat")

# Define tasks
analyze_query_task = cl.Task(
    title="Analyzing the query",
    status=cl.TaskStatus.READY,
    forId="analyze_query_task")

ms_docs_search_task = cl.Task(
    title="Searching Microsoft docs",
    status=cl.TaskStatus.READY,
    forId="ms_docs_search_task")

retrieve_kb_task = cl.Task(
    title="Searching the knowledge base",
    status=cl.TaskStatus.READY,
    forId="retrieve_kb_task")

aggregate_results_task = cl.Task(
    title="Aggregating results",
    status=cl.TaskStatus.READY,
    forId="aggregate_results_task")

generate_final_output_task = cl.Task(
    title="Generating final output",
    status=cl.TaskStatus.READY,
    forId="generate_final_output_task")


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
            start_executor=preprocess_query,
            output_executors=[generate_final_output])
        .add_fan_out_edges(preprocess_query, [search_ms_docs, retrieve_knowledge_base])
        .add_fan_in_edges([search_ms_docs, retrieve_knowledge_base], aggregate_results)
        .add_edge(aggregate_results, generate_final_output)        
        .build())

    return compliance_workflow


@executor(id="preprocess_query")
async def preprocess_query(messages: list[Message],
                           ctx: WorkflowContext[PreprocessOutput]) -> None:
    """Executor to preprocess the input messages.
    Args:
        messages (list[Message]): The list of chat messages.
        chat_thread (AgentThread): The current chat thread.
    Returns:
        PreprocessOutput: The preprocessed output containing messages, chat thread, and task list.
    """
    # Send a thinking message
    await cl.Message("Planning...").send()

    # Update the analyze query task status
    analyze_query_task.status = cl.TaskStatus.DONE
    ms_docs_search_task.status = cl.TaskStatus.READY
    retrieve_kb_task.status = cl.TaskStatus.READY    
    aggregate_results_task.status = cl.TaskStatus.READY
    generate_final_output_task.status = cl.TaskStatus.READY

    # Create a new task list
    task_list = cl.TaskList(
        name="compliance_workflow_tasks",
        title="Compliance Workflow Tasks",
        status="⌛ Running…",
        tasks=[
            analyze_query_task,
            ms_docs_search_task,
            retrieve_kb_task,            
            aggregate_results_task,
            generate_final_output_task
        ])
    await task_list.update()

    # Prepare the output
    output = PreprocessOutput(
        messages=messages,
        task_list=task_list)

    # Send the output to the next executor
    await ctx.send_message(output)


@executor(id="retrieve_knowledge_base")
async def retrieve_knowledge_base(input: PreprocessOutput,
                                  ctx: WorkflowContext[KnowledgeBaseOutput]) -> None:
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
        task_list=input.task_list)

    # Update the task status
    retrieve_kb_task.status = cl.TaskStatus.DONE
    await input.task_list.update()

    # Return the output to the next executor
    await ctx.send_message(output)


@executor(id="search_ms_docs")
async def search_ms_docs(input: PreprocessOutput, ctx: WorkflowContext[MSDocsOutput]) -> None:
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
        url="https://learn.microsoft.com/api/mcp")

    # Create the agent
    microsoft_docs_agent = Agent(
        client=foundry_client,
        name="microsoft_docs_agent",
        description="Microsoft Docs agent that searches for relevant Microsoft documentation.",
        instructions="""
                You provide information from Microsoft Docs using the search tool.
                - Rephrase the query into multiple relevant intent queries for better search results
                - Call the tool maximum 3 times at a time with different queries
                - Cite sources with links and include all images from search results
                - Format responses in markdown with proper headers no bigger than `###`
                - Add relevant icons to headers based on the content
                - Use an official tone
            """,
        tools=[mcp_server],
        allow_multiple_tool_calls=True)

    # Run the agent with the query
    response = await microsoft_docs_agent.run(input.messages)

    # Prepare the output
    output = MSDocsOutput(
        answer=response.text,
        task_list=input.task_list)

    # Update the task status
    ms_docs_search_task.status = cl.TaskStatus.DONE
    await input.task_list.update()

    # Return a placeholder response
    await ctx.send_message(output)


@executor(id="aggregate_results")
async def aggregate_results(results: list[Any],
                            ctx: WorkflowContext[AggregateOutput]) -> None:
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

    # Aggregate the results
    aggregated_response = f"> ## 📃 Knowledge Base Results: \n{kb_output.answer}\n --- \n> ## 📚 Microsoft Docs Results: \n{ms_docs_output.answer}"

    # Prepare the output
    output = AggregateOutput(
        aggregated_response=aggregated_response,
        task_list=kb_output.task_list)

    # Update the task list status to completed
    aggregate_results_task.status = cl.TaskStatus.DONE
    await kb_output.task_list.update()

    # Return the final aggregated output
    await ctx.send_message(output)


@executor(id="generate_final_output")
async def generate_final_output(input: AggregateOutput,
                                ctx: WorkflowContext[Never, str]) -> None:
    """Executor to generate the final output response.
    Args:
        aggregated_response (str): The aggregated response from previous executors.
    Returns:
        str: The final formatted response.
    """
    # Here you can add any final formatting or processing if needed
    # Placeholder for any additional processing
    final_response = input.aggregated_response

    # Update the task status
    generate_final_output_task.status = cl.TaskStatus.DONE
    input.task_list.status = "✅ Completed"
    await input.task_list.update()
    await input.task_list.remove()

    # Return the final response
    await ctx.yield_output(final_response)


async def _retrieve_knowledge_new(query: str) -> str:
    query += "\n**Format responses in Markdown with proper headers no bigger than `###`. Use an official tone.**"

    search_provider = AzureAISearchContextProvider(
        endpoint=os.getenv("AI_SEARCH_ENDPOINT"),
        knowledge_base_name=os.getenv("KNOWLEDGE_BASE_NAME", "kb-compliance-general"),        
        mode="agentic",
        credential=credential,
        retrieval_reasoning_effort="medium",
        timeout=180,
        knowledge_base_output_mode="answerSynthesis",
        api_version=ai_search_api_version,
        azure_openai_resource_url=os.getenv("AZURE_OPENAI_ENDPOINT"),
        top_k=5,
    )
    
    agent = Agent(
        client=foundry_client,
        model="gpt-5",
        context_providers=[search_provider]
    )
    
    session = agent.create_session()    
    response = await agent.run(query, session=session)
    return response.text


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

    # Generate an access token using DefaultAzureCredential
    token_response = credential.get_token("https://search.azure.com/.default")    

    # Prepare headers and payload for the request
    headers = {        
        "Content-Type": "application/json",
        "Authorization": f"Bearer {token_response.token}"
        #"api-key": ai_search_api_key        
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

    storage_sas_token = storage_account_service.generate_sas_token(
        container_name=compliance_container_name, expiry_weeks=1)

    storage_url = f"https://{storage_account_name}.blob.core.windows.net/{compliance_container_name}"

    # Extract unique reference titles
    references_list_items = []
    for ref in sorted(response_json.get("references", []), key=lambda x: int(x['id'])):
        page_num = _extract_page(ref['docKey'])
        reference_line = f"{ref['id']}. [{ref['title']}]({storage_url}/{quote(ref['title'])}?{storage_sas_token}#page={page_num}) - (Page #{page_num})"
        references_list_items.append(reference_line)

    references_list = "\n".join(references_list_items)

    # Combine response text with references
    processed_answer = f"{refined_response_text}\n\n### References:\n{references_list}"

    return processed_answer


def _extract_page(doc_key: str) -> str:
    # Extract the page number or relevant information from the docKey
    # Assuming the docKey format contains the page number after a specific delimiter, e.g., "_pages_"
    if "_pages_" in doc_key:
        return doc_key.split("_pages_")[-1]
    return "Undefined"
