import os
import re
import json
import base64
from dotenv import load_dotenv

# Add references
from azure.identity import DefaultAzureCredential
from azure.ai.projects import AIProjectClient
from azure.ai.projects.models import PromptAgentDefinition, MCPTool
from openai.types.responses.response_input_param import McpApprovalResponse, ResponseInputParam


def save_png_from_response(response, path):
    output_text = (getattr(response, "output_text", "") or "").replace("\\u002b", "+").replace("\\u002B", "+")
    match = re.search(r"data:image/png;base64,([A-Za-z0-9+/]+=*)", output_text)
    if match:
        b64 = match.group(1).rstrip("=")
        b64 += "=" * (-len(b64) % 4)
        with open(path, "wb") as f:
            f.write(base64.b64decode(b64))
        return True
    for item in response.output:
        if getattr(item, "type", None) == "mcp_call":
            if getattr(item, "status", None) == "failed":
                print(f"  MCP call '{getattr(item, 'name', '?')}' failed: {getattr(item, 'error', 'unknown error')}")
                continue
            output_str = getattr(item, "output", None)
            if output_str:
                try:
                    for entry in json.loads(output_str):
                        if isinstance(entry, dict) and entry.get("type") == "image":
                            b64 = entry.get("data", "")
                            if b64:
                                with open(path, "wb") as f:
                                    f.write(base64.b64decode(b64))
                                return True
                except Exception:
                    pass
        blob = item.model_dump_json() if hasattr(item, "model_dump_json") else str(item)
        blob = blob.replace("\\/", "/").replace("\\u002b", "+").replace("\\u002B", "+")
        match = re.search(r"iVBORw0KGgo[A-Za-z0-9+/]+={0,2}", blob)
        if match:
            try:
                with open(path, "wb") as f:
                    f.write(base64.b64decode(match.group(0)))
                return True
            except Exception:
                pass
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

        # Offer three preset questions, one per MCP server
        questions = {
            "1": "Generate a QR code for https://www.integrations.at.",
            "2": "How many bags of Espresso Blend are in stock?",
            "3": "How do I publish a Python function as a tool on a FastMCP server?",
        }

        try:
            while True:
                print("\nChoose a question (or press Enter to exit):")
                print("  1 - QR code server (generate a QR code)")
                print("  2 - Roastery server (Espresso Blend stock)")
                print("  3 - Microsoft Learn server (FastMCP docs)")
                choice = input("\n> ").strip()
                if not choice:
                    break
                question = questions.get(choice)
                if not question:
                    print("  Invalid choice, pick 1, 2, or 3.")
                    continue
                print(f"\nAsking: {question}")

                # A fresh conversation per question keeps each approval flow isolated
                conversation = openai_client.conversations.create()

                response = openai_client.responses.create(
                    conversation=conversation.id,
                    input=question,
                    extra_body={"agent_reference": {"name": agent.name, "type": "agent_reference"}},
                )

                # Approve all MCP tool calls in a loop until the agent is done
                while True:
                    input_list: ResponseInputParam = [
                        McpApprovalResponse(
                            type="mcp_approval_response",
                            approve=True,
                            approval_request_id=item.id,
                        )
                        for item in response.output
                        if item.type == "mcp_approval_request"
                        and item.server_label in ("api-specs", "roastery", "qr-code")
                        and item.id
                    ]
                    if not input_list:
                        break
                    response = openai_client.responses.create(
                        input=input_list,
                        previous_response_id=response.id,
                        extra_body={"agent_reference": {"name": agent.name, "type": "agent_reference"}},
                    )

                print(f"\nAgent response: {response.output_text}")

                qr_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "qr-code.png")
                if save_png_from_response(response, qr_path):
                    print(f"\nQR code saved to: {qr_path}")

                openai_client.conversations.delete(conversation_id=conversation.id)
        finally:
            # Clean up the agent version once the user is done testing
            project_client.agents.delete_version(agent_name=agent.name, agent_version=agent.version)
            print("\nAgent deleted")


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\nInterrupted. Exiting.")
