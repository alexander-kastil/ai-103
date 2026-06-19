import os
import asyncio
import json
from dotenv import load_dotenv
from contextlib import AsyncExitStack

from azure.identity import DefaultAzureCredential
from azure.ai.projects import AIProjectClient
from azure.ai.projects.models import PromptAgentDefinition, FunctionTool
from openai.types.responses.response_input_param import FunctionCallOutput, ResponseInputParam

# Add references
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


# Clear the console
os.system('cls' if os.name == 'nt' else 'clear')

# Load environment variables from .env file
load_dotenv()
project_endpoint = os.getenv("PROJECT_ENDPOINT")
model_deployment = os.getenv("MODEL_DEPLOYMENT_NAME")


async def connect_to_server(exit_stack: AsyncExitStack):
    server_params = StdioServerParameters(
        command="python",
        args=["server.py"],
        env=None,
    )

    # Start the MCP server
    stdio_transport = await exit_stack.enter_async_context(stdio_client(server_params))
    stdio, write = stdio_transport

    # Create an MCP client session
    session = await exit_stack.enter_async_context(ClientSession(stdio, write))
    await session.initialize()

    # List available tools
    response = await session.list_tools()
    tools = response.tools
    print("\nConnected to roastery MCP server with tools:", [tool.name for tool in tools])

    return session


async def chat_loop(session):

    # Connect to the agents client
    with (
        DefaultAzureCredential(
            exclude_environment_credential=True,
            exclude_managed_identity_credential=True,
        ) as credential,
        AIProjectClient(endpoint=project_endpoint, credential=credential) as project_client,
        project_client.get_openai_client() as openai_client,
    ):

        # Get the mcp tools available from the server
        response = await session.list_tools()
        tools = response.tools

        # Build a function for each tool
        def make_tool_func(tool_name):
            async def tool_func(**kwargs):
                result = await session.call_tool(tool_name, kwargs)
                return result

            tool_func.__name__ = tool_name
            return tool_func

        # Store the functions in a dictionary for easy access when processing function calls
        functions_dict = {tool.name: make_tool_func(tool.name) for tool in tools}

        # Create FunctionTool definitions for the agent
        mcp_function_tools = []
        for tool in tools:
            function_tool = FunctionTool(
                name=tool.name,
                description=tool.description,
                parameters={
                    "type": "object",
                    "properties": {},
                    "additionalProperties": False,
                },
                strict=True,
            )
            mcp_function_tools.append(function_tool)

        # Create the agent
        agent = project_client.agents.create_version(
            agent_name="roastery-agent",
            definition=PromptAgentDefinition(
                model=model_deployment,
                instructions="""
                You are an inventory assistant for an artisan coffee roastery.
                Stock levels and sales are measured in 1 kg bags. Here are some general guidelines:
                - Recommend a restock when bean stock < 10 and weekly sales > 15
                - Recommend a clearance when bean stock > 20 and weekly sales < 5
                Use the available tools to look up current stock and weekly sales before answering.
                """,
                tools=mcp_function_tools,
            ),
        )
        print(f"Created agent '{agent.name}' (version {agent.version}).")

        # Create a conversation for the chat session
        conversation = openai_client.conversations.create()

        # Create an input list to hold function call outputs to send back to the model
        input_list: ResponseInputParam = []

        try:
            while True:
                user_input = input(
                    "\nEnter a prompt for the roastery agent. Use 'quit' to exit.\n[default: Which coffees should I restock this week?]\nUSER: "
                ).strip()
                if not user_input:
                    user_input = "Which coffees should I restock this week?"
                if user_input.lower() == "quit":
                    print("Exiting chat.")
                    break
                if not user_input:
                    continue

                # Send a prompt to the agent
                openai_client.conversations.items.create(
                    conversation_id=conversation.id,
                    items=[{"type": "message", "role": "user", "content": user_input}],
                )

                # Reset the input list and retrieve the agent's response, which may
                # include function calls to the MCP server tools
                input_list = []
                response = openai_client.responses.create(
                    conversation=conversation.id,
                    extra_body={"agent_reference": {"name": agent.name, "type": "agent_reference"}},
                    input=input_list,
                )

                # Check the run status for failures
                if response.status == "failed":
                    print(f"Response failed: {response.error}")
                    continue

                # Process function calls
                for item in response.output:
                    if item.type == "function_call":
                        # Retrieve the matching function tool
                        function_name = item.name
                        kwargs = json.loads(item.arguments)
                        print(f"  [tool call] {function_name}({kwargs})")
                        required_function = functions_dict.get(function_name)

                        # Invoke the function
                        output = await required_function(**kwargs)

                        # Append the output text
                        input_list.append(
                            FunctionCallOutput(
                                type="function_call_output",
                                call_id=item.call_id,
                                output=output.content[0].text,
                            )
                        )

                # Send function call outputs back to the model and retrieve a response
                if input_list:
                    response = openai_client.responses.create(
                        input=input_list,
                        previous_response_id=response.id,
                        extra_body={"agent_reference": {"name": agent.name, "type": "agent_reference"}},
                    )

                print(f"\nAGENT: {response.output_text}")
        finally:
            # Delete the agent and conversation when done
            print("\nCleaning up agent and conversation.")
            openai_client.conversations.delete(conversation_id=conversation.id)
            project_client.agents.delete_version(agent_name=agent.name, agent_version=agent.version)
            print("Deleted roastery agent.")


async def main():
    exit_stack = AsyncExitStack()
    try:
        session = await connect_to_server(exit_stack)
        await chat_loop(session)
    except asyncio.CancelledError:
        pass
    finally:
        try:
            await exit_stack.aclose()
        except (asyncio.CancelledError, Exception):
            pass


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nInterrupted.")
