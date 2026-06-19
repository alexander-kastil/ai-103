import os
import re
import base64
from dotenv import load_dotenv

# Add references
from azure.identity import DefaultAzureCredential
from azure.ai.projects import AIProjectClient
from azure.ai.projects.models import PromptAgentDefinition, MCPTool
from openai.types.responses.response_input_param import McpApprovalResponse, ResponseInputParam


def save_png_from_response(response, path):
    for item in response.output:
        blob = item.model_dump_json() if hasattr(item, "model_dump_json") else str(item)
        blob = blob.replace("\\/", "/")
        match = re.search(r"iVBORw0KGgo[A-Za-z0-9+/]+={0,2}", blob)
        if match:
            with open(path, "wb") as file:
                file.write(base64.b64decode(match.group(0)))
            return True
    return False


def main():
    # Clear the console
    os.system('cls' if os.name == 'nt' else 'clear')

    # Load environment variables from .env file
    load_dotenv()
    project_endpoint = os.getenv("PROJECT_ENDPOINT")
    model_deployment = os.getenv("MODEL_DEPLOYMENT_NAME")
    roastery_mcp_url = os.getenv("ROASTERY_MCP_URL")
    qr_mcp_url = os.getenv("QR_MCP_URL")

    # Connect to the agents client
    with (
        DefaultAzureCredential(
            exclude_environment_credential=True,
            exclude_managed_identity_credential=True,
        ) as credential,
        AIProjectClient(endpoint=project_endpoint, credential=credential) as project_client,
        project_client.get_openai_client() as openai_client,
    ):

        # Initialize the remote Microsoft Learn MCP tool
        docs_mcp_tool = MCPTool(
            server_label="api-specs",
            server_url="https://learn.microsoft.com/api/mcp",
            require_approval="always",
        )

        # Initialize the local roastery FastMCP tool exposed over a public HTTPS URL
        roastery_mcp_tool = MCPTool(
            server_label="roastery",
            server_url=roastery_mcp_url,
            require_approval="always",
        )

        # Initialize the standalone QR code MCP tool exposed over a public HTTPS URL
        qr_mcp_tool = MCPTool(
            server_label="qr-code",
            server_url=qr_mcp_url,
            require_approval="always",
        )

        # Create a new agent with all three MCP tools attached
        agent = project_client.agents.create_version(
            agent_name="docs-agent",
            definition=PromptAgentDefinition(
                model=model_deployment,
                instructions=(
                    "You are a helpful assistant that can use MCP tools to assist users. "
                    "Use the Microsoft Learn tools to answer documentation questions, the "
                    "roastery tools to answer questions about coffee bean inventory and weekly sales, "
                    "and the QR code tool to generate QR codes from URLs or text."
                ),
                tools=[docs_mcp_tool, roastery_mcp_tool, qr_mcp_tool],
            ),
        )
        print(f"Agent created (id: {agent.id}, name: {agent.name}, version: {agent.version})")

        # Create a conversation thread
        conversation = openai_client.conversations.create()
        print(f"Created conversation (id: {conversation.id})")

        # Offer three preset questions, one per MCP server
        questions = {
            "1": "Generate a QR code for https://www.integrations.at.",
            "2": "How many bags of Espresso Blend are in stock?",
            "3": "How do I publish a Python function as a tool on a FastMCP server?",
        }

        try:
            print("\nChoose a question:")
            print("  Press 1 for the QR code server (generate a QR code)")
            print("  Press 2 for the roastery server (Espresso Blend stock)")
            print("  Press 3 for the Microsoft Learn server (FastMCP docs)")
            choice = input("\n> ").strip() or "1"
            question = questions.get(choice, questions["1"])
            print(f"\nAsking: {question}")

            response = openai_client.responses.create(
                conversation=conversation.id,
                input=question,
                extra_body={"agent_reference": {"name": agent.name, "type": "agent_reference"}},
            )

            # Process any MCP approval requests that were generated
            input_list: ResponseInputParam = []
            for item in response.output:
                if item.type == "mcp_approval_request":
                    if item.server_label in ("api-specs", "roastery", "qr-code") and item.id:
                        input_list.append(
                            McpApprovalResponse(
                                type="mcp_approval_response",
                                approve=True,
                                approval_request_id=item.id,
                            )
                        )

            # Send the approval response back and retrieve a response
            response = openai_client.responses.create(
                input=input_list,
                previous_response_id=response.id,
                extra_body={"agent_reference": {"name": agent.name, "type": "agent_reference"}},
            )

            print(f"\nAgent response: {response.output_text}")

            qr_path = os.path.abspath("qr-code.png")
            if save_png_from_response(response, qr_path):
                print(f"\nQR code saved to: {qr_path}")
        finally:
            # Clean up resources by deleting the agent version and conversation
            openai_client.conversations.delete(conversation_id=conversation.id)
            project_client.agents.delete_version(agent_name=agent.name, agent_version=agent.version)
            print("\nAgent deleted")


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\nInterrupted. Exiting.")
