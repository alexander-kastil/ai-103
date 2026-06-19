import os
import sys
import asyncio
import json
from dotenv import load_dotenv
from contextlib import AsyncExitStack
from azure.ai.projects import AIProjectClient
from azure.ai.projects.models import FunctionTool
from azure.identity import DefaultAzureCredential
from azure.ai.projects.models import PromptAgentDefinition, FunctionTool
from openai.types.responses.response_input_param import FunctionCallOutput, ResponseInputParam

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

os.system('cls' if os.name == 'nt' else 'clear')

load_dotenv()
project_endpoint = os.getenv("PROJECT_ENDPOINT")
model_deployment = os.getenv("MODEL_DEPLOYMENT_NAME")

DEFAULT_PROMPT = "Show me the current inventory levels for all products."


async def connect_to_server(exit_stack: AsyncExitStack):
    server_params = StdioServerParameters(
        command=sys.executable,
        args=["server.py"],
        env=None
    )

    stdio_transport = await exit_stack.enter_async_context(stdio_client(server_params))
    stdio, write = stdio_transport

    session = await exit_stack.enter_async_context(ClientSession(stdio, write))
    await session.initialize()

    response = await session.list_tools()
    tools = response.tools
    print("\nConnected to server with tools:", [tool.name for tool in tools])

    return session


async def chat_loop(session):

    with (
        DefaultAzureCredential() as credential,
        AIProjectClient(endpoint=project_endpoint, credential=credential) as project_client,
        project_client.get_openai_client() as openai_client,
    ):

        response = await session.list_tools()
        tools = response.tools

        def make_tool_func(tool_name):
            async def tool_func(**kwargs):
                result = await session.call_tool(tool_name, kwargs)
                return result

            tool_func.__name__ = tool_name
            return tool_func

        functions_dict = {tool.name: make_tool_func(tool.name) for tool in tools}

        mcp_function_tools: FunctionTool = []
        for tool in tools:
            function_tool = FunctionTool(
                name=tool.name,
                description=tool.description,
                parameters={
                    "type": "object",
                    "properties": {},
                    "additionalProperties": False,
                },
                strict=True
            )
            mcp_function_tools.append(function_tool)

        agent = project_client.agents.create_version(
            agent_name="inventory-agent",
            definition=PromptAgentDefinition(
                model=model_deployment,
                instructions="""
                You are an inventory assistant. Here are some general guidelines:
                - Recommend restock if item inventory < 10  and weekly sales > 15
                - Recommend clearance if item inventory > 20 and weekly sales < 5
                """,
                tools=mcp_function_tools
            ),
        )

        conversation = openai_client.conversations.create()

        input_list: ResponseInputParam = []

        while True:
            user_input = input(f"Enter a prompt for the inventory agent. Use 'quit' to exit.\n[default: {DEFAULT_PROMPT}]\nUSER: ").strip()
            if user_input.lower() == "quit":
                print("Exiting chat.")
                break
            if not user_input:
                user_input = DEFAULT_PROMPT

            openai_client.conversations.items.create(
                conversation_id=conversation.id,
                items=[{"type": "message", "role": "user", "content": user_input}],
            )

            response = openai_client.responses.create(
                conversation=conversation.id,
                extra_body={"agent_reference": {"name": agent.name, "type": "agent_reference"}},
                input=input_list,
            )

            if response.status == "failed":
                print(f"Response failed: {response.error}")

            input_list = []
            for item in response.output:
                if item.type == "function_call":
                    function_name = item.name
                    kwargs = json.loads(item.arguments)
                    required_function = functions_dict.get(function_name)

                    output = await required_function(**kwargs)

                    input_list.append(
                        FunctionCallOutput(
                            type="function_call_output",
                            call_id=item.call_id,
                            output=output.content[0].text,
                        )
                    )

            if input_list:
                response = openai_client.responses.create(
                    input=input_list,
                    previous_response_id=response.id,
                    extra_body={"agent_reference": {"name": agent.name, "type": "agent_reference"}},
                )
            print(f"Agent response: {response.output_text}")
            input_list = []

        print("Cleaning up agents:")
        project_client.agents.delete_version(agent_name=agent.name, agent_version=agent.version)
        print("Deleted inventory agent.")


async def main():
    exit_stack = AsyncExitStack()
    try:
        session = await connect_to_server(exit_stack)
        await chat_loop(session)
    except (KeyboardInterrupt, asyncio.CancelledError):
        print("\nInterrupted.")
    finally:
        try:
            await exit_stack.aclose()
        except Exception:
            pass


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nInterrupted.")
