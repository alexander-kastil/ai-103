import os
import json
from dotenv import load_dotenv

# Add references
from azure.identity import DefaultAzureCredential
from azure.ai.projects import AIProjectClient
from azure.ai.projects.models import PromptAgentDefinition, FunctionTool
from openai.types.responses.response_input_param import FunctionCallOutput

from functions import (
    next_visible_event,
    calculate_observation_cost,
    generate_observation_report,
)


def main():
    # Clear the console
    os.system('cls' if os.name == 'nt' else 'clear')

    # Load environment variables from .env file
    load_dotenv()
    project_endpoint = os.getenv("PROJECT_ENDPOINT")
    model_deployment = os.getenv("MODEL_DEPLOYMENT_NAME")

    # Connect to the project client
    project_client = AIProjectClient(
        endpoint=project_endpoint,
        credential=DefaultAzureCredential(
            exclude_environment_credential=True,
            exclude_managed_identity_credential=True,
        ),
    )
    openai_client = project_client.get_openai_client()

    # Define the event function tool
    event_tool = FunctionTool(
        name="next_visible_event",
        description="Get the next visible astronomical event for a given location (continent).",
        parameters={
            "type": "object",
            "properties": {
                "location": {
                    "type": "string",
                    "description": "Continent to find the next visible event in, e.g. 'South America'."
                }
            },
            "required": ["location"],
            "additionalProperties": False
        },
        strict=True
    )

    # Define the observation cost function tool
    cost_tool = FunctionTool(
        name="calculate_observation_cost",
        description="Calculate the cost of telescope observation time based on the tier, hours, and priority.",
        parameters={
            "type": "object",
            "properties": {
                "telescope_tier": {
                    "type": "string",
                    "description": "Telescope tier: standard, advanced, or premium."
                },
                "hours": {
                    "type": "number",
                    "description": "Number of observation hours to book."
                },
                "priority": {
                    "type": "string",
                    "description": "Booking priority: low, normal, high, or urgent."
                }
            },
            "required": ["telescope_tier", "hours", "priority"],
            "additionalProperties": False
        },
        strict=True
    )

    # Define the observation report generation function tool
    report_tool = FunctionTool(
        name="generate_observation_report",
        description="Generate and save an observation session report summarizing the event, booking, and cost.",
        parameters={
            "type": "object",
            "properties": {
                "event_name": {"type": "string", "description": "Name of the astronomical event."},
                "location": {"type": "string", "description": "Continent where the event is observed."},
                "telescope_tier": {"type": "string", "description": "Telescope tier: standard, advanced, or premium."},
                "hours": {"type": "number", "description": "Number of observation hours booked."},
                "priority": {"type": "string", "description": "Booking priority: low, normal, high, or urgent."},
                "observer_name": {"type": "string", "description": "Name of the observer the report is for."}
            },
            "required": ["event_name", "location", "telescope_tier", "hours", "priority", "observer_name"],
            "additionalProperties": False
        },
        strict=True
    )

    # Create a new agent with the function tools
    agent = project_client.agents.create_version(
        agent_name="astronomy-agent",
        definition=PromptAgentDefinition(
            model=model_deployment,
            instructions="""You are an astronomy observations assistant that helps
users find information about astronomical events and calculate
telescope rental costs. Use the available tools to assist.""",
            tools=[event_tool, cost_tool, report_tool]
        )
    )
    print(f"Created agent '{agent.name}' (version {agent.version}).\n")

    agent_reference = {"name": agent.name, "type": "agent_reference"}

    # Create a conversation for the chat session
    conversation = openai_client.conversations.create()

    sample_prompt = "Find the next event visible from South America and calculate costs for 5 hours of premium telescope time at normal priority."

    try:
        while True:
            try:
                user_input = input(f"Enter a prompt (or press Enter to use sample, 'quit' to exit).\n[{sample_prompt}]\nUSER: ").strip()
            except KeyboardInterrupt:
                print("\nExiting chat.")
                break
            if user_input.lower() == "quit":
                print("Exiting chat.")
                break
            if not user_input:
                user_input = sample_prompt
                print(f"Using sample: {user_input}")

            # Send a prompt to the agent
            response = openai_client.responses.create(
                input=user_input,
                conversation=conversation.id,
                extra_body={"agent_reference": agent_reference},
            )

            # Retrieve the agent's response, which may include function calls.
            # Loop so chained tool calls (e.g. find event -> calculate cost) all resolve.
            while True:
                # Process function calls
                function_outputs = []
                for item in response.output:
                    if item.type == "function_call":
                        args = json.loads(item.arguments)
                        print(f"  [tool call] {item.name}({args})")

                        if item.name == "next_visible_event":
                            result = next_visible_event(**args)
                        elif item.name == "calculate_observation_cost":
                            result = calculate_observation_cost(**args)
                        elif item.name == "generate_observation_report":
                            result = generate_observation_report(**args)
                        else:
                            result = json.dumps({"error": f"Unknown function '{item.name}'"})

                        function_outputs.append(
                            FunctionCallOutput(
                                type="function_call_output",
                                call_id=item.call_id,
                                output=result,
                            )
                        )

                if not function_outputs:
                    break

                # Send function call outputs back to the model and retrieve a response
                response = openai_client.responses.create(
                    input=function_outputs,
                    conversation=conversation.id,
                    extra_body={"agent_reference": agent_reference},
                )

            print(f"\nAGENT: {response.output_text}\n")
    finally:
        # Delete the agent and conversation when done
        openai_client.conversations.delete(conversation_id=conversation.id)
        project_client.agents.delete_version(agent_name=agent.name, agent_version=agent.version)
        print("Cleaned up agent and conversation.")


if __name__ == '__main__':
    main()
