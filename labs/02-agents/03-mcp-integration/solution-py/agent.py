import os
from dotenv import load_dotenv

from azure.identity import DefaultAzureCredential
from azure.ai.projects import AIProjectClient
from azure.ai.projects.models import PromptAgentDefinition, MCPTool
from openai.types.responses.response_input_param import McpApprovalResponse, ResponseInputParam

load_dotenv()
project_endpoint = os.getenv("PROJECT_ENDPOINT")
model_deployment = os.getenv("MODEL_DEPLOYMENT_NAME")

DEFAULT_PROMPT = "Give me the Azure CLI commands to create an Azure Container App with a managed identity."


def main():
    with (
        DefaultAzureCredential() as credential,
        AIProjectClient(endpoint=project_endpoint, credential=credential) as project_client,
        project_client.get_openai_client() as openai_client,
    ):
        mcp_tool = MCPTool(
            server_label="api-specs",
            server_url="https://learn.microsoft.com/api/mcp",
            require_approval="always",
        )

        agent = project_client.agents.create_version(
            agent_name="MyAgent",
            definition=PromptAgentDefinition(
                model=model_deployment,
                instructions="You are a helpful agent that can use MCP tools to assist users. Use the available MCP tools to answer questions and perform tasks.",
                tools=[mcp_tool],
            ),
        )
        print(f"Agent created (id: {agent.id}, name: {agent.name}, version: {agent.version})")

        conversation = openai_client.conversations.create()
        print(f"Created conversation (id: {conversation.id})")

        user_input = input(f"Enter a prompt for the agent [default: {DEFAULT_PROMPT}]\nUSER: ").strip()
        if not user_input:
            user_input = DEFAULT_PROMPT

        response = openai_client.responses.create(
            conversation=conversation.id,
            input=user_input,
            extra_body={"agent_reference": {"name": agent.name, "type": "agent_reference"}},
        )

        while True:
            input_list: ResponseInputParam = []
            for item in response.output:
                if item.type == "mcp_approval_request":
                    if item.server_label == "api-specs" and item.id:
                        input_list.append(
                            McpApprovalResponse(
                                type="mcp_approval_response",
                                approve=True,
                                approval_request_id=item.id,
                            )
                        )

            if not input_list:
                break

            print("Final input:")
            print(input_list)

            response = openai_client.responses.create(
                input=input_list,
                previous_response_id=response.id,
                extra_body={"agent_reference": {"name": agent.name, "type": "agent_reference"}},
            )

        print(f"\nAgent response: {response.output_text}")

        project_client.agents.delete_version(agent_name=agent.name, agent_version=agent.version)
        print("Agent deleted")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nInterrupted.")
