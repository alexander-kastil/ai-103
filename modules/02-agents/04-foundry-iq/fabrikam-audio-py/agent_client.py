import os
import json
from dotenv import load_dotenv
from azure.identity import DefaultAzureCredential
from azure.ai.projects import AIProjectClient

# Load environment variables
load_dotenv()
project_endpoint = os.getenv("PROJECT_ENDPOINT")
agent_name = os.getenv("AGENT_NAME")

# Validate configuration
if not project_endpoint or not agent_name:
    raise ValueError("PROJECT_ENDPOINT and AGENT_NAME must be set in the .env file")

# Connect to the project and agent
credential = DefaultAzureCredential(
    exclude_environment_credential=True,
    exclude_managed_identity_credential=True,
)
project_client = AIProjectClient(
    credential=credential,
    endpoint=project_endpoint,
)

# Get the OpenAI client
openai_client = project_client.get_openai_client()

# Get the agent
agent = project_client.agents.get(agent_name=agent_name)

# Create a new conversation
conversation = openai_client.conversations.create(items=[])

# Conversation history for context (client-side tracking)
conversation_history = []


def send_message_to_agent(user_message):
    """
    Send a message to the agent and handle the response using the conversations API.
    Handles the Foundry IQ (MCP) approval flow when the agent asks to search the
    knowledge base.
    """
    try:
        print("\nAgent: ", end="", flush=True)

        # Add the user message to the conversation
        openai_client.conversations.items.create(
            conversation_id=conversation.id,
            items=[{"type": "message", "role": "user", "content": user_message}],
        )

        # Store in conversation history (client-side)
        conversation_history.append({"role": "user", "content": user_message})

        # Create a response using the agent
        response = openai_client.responses.create(
            conversation=conversation.id,
            extra_body={"agent_reference": {"name": agent.name, "type": "agent_reference"}},
            input="",
        )

        # Check if the response output contains an MCP approval request
        approval_request = None
        if hasattr(response, "output") and response.output:
            for item in response.output:
                if hasattr(item, "type") and item.type == "mcp_approval_request":
                    approval_request = item
                    break

        # Handle approval request if present
        if approval_request:
            print(f"\n[Approval required for: {approval_request.name}]")
            print(f"Server: {approval_request.server_label}")

            # Parse and display the arguments (for transparency)
            try:
                args = json.loads(approval_request.arguments)
                print(f"Arguments: {json.dumps(args, indent=2)}\n")
            except Exception:
                print(f"Arguments: {approval_request.arguments}\n")

            # Prompt user for approval
            approval_input = input("Approve this action? (yes/no) [default: yes]: ").strip().lower()
            if not approval_input:
                approval_input = "yes"

            if approval_input in ["yes", "y"]:
                print("Approving action...\n")
                approval_response = {
                    "type": "mcp_approval_response",
                    "approval_request_id": approval_request.id,
                    "approve": True,
                }
            else:
                print("Action denied.\n")
                approval_response = {
                    "type": "mcp_approval_response",
                    "approval_request_id": approval_request.id,
                    "approve": False,
                }

            # Add the approval response to the conversation
            openai_client.conversations.items.create(
                conversation_id=conversation.id,
                items=[approval_response],
            )

            # Get the actual response after approval/denial
            response = openai_client.responses.create(
                conversation=conversation.id,
                extra_body={"agent_reference": {"name": agent.name, "type": "agent_reference"}},
                input="",
            )

        # Extract the response text
        if response and response.output_text:
            response_text = response.output_text
            print(f"{response_text}\n")

            # Check for citations if available
            if hasattr(response, "citations") and response.citations:
                print("Sources:")
                for citation in response.citations:
                    label = citation.content if hasattr(citation, "content") else "Knowledge Base"
                    print(f"  - {label}")

            # Store in conversation history (client-side)
            conversation_history.append({"role": "assistant", "content": response_text})

            return response_text
        else:
            print("No response received.\n")
            return None
    except Exception as e:
        print(f"\n\nError: {str(e)}\n")
        return None


def display_conversation_history():
    """Display the full conversation history."""
    print("\n" + "=" * 60)
    print("CONVERSATION HISTORY")
    print("=" * 60 + "\n")

    for turn in conversation_history:
        role = turn["role"].upper()
        content = turn["content"]
        print(f"{role}: {content}\n")

    print("=" * 60 + "\n")


def main():
    """Main interaction loop."""
    # Clear the console
    os.system('cls' if os.name == 'nt' else 'clear')

    print(f"Connected to agent: {agent.name} (id: {agent.id})")
    print(f"Created conversation (id: {conversation.id})\n")

    print("Fabrikam Audio Product Expert Agent")
    print("Ask questions about our speakers, soundbars, and headphones.")
    print("Type 'history' to see the conversation history, or 'quit' to exit.\n")

    while True:
        try:
            user_input = input("You [default: What types of products does Fabrikam Audio offer?]: ").strip()

            if not user_input:
                user_input = "What types of products does Fabrikam Audio offer?"

            if user_input.lower() == "quit":
                print("\nEnding conversation...")
                break

            if user_input.lower() == "history":
                display_conversation_history()
                continue

            # Send message and get response
            send_message_to_agent(user_input)

        except KeyboardInterrupt:
            print("\n\nInterrupted by user.")
            break
        except Exception as e:
            print(f"\nUnexpected error: {str(e)}\n")

    print("\nConversation ended.")


if __name__ == "__main__":
    main()
