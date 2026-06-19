import os
import asyncio
from pathlib import Path

# Add references
from agent_framework import tool, Agent
from agent_framework.azure import AzureOpenAIResponsesClient
from azure.identity import AzureCliCredential
from dotenv import load_dotenv
from pydantic import Field
from typing import Annotated


async def main():
    # Clear the console
    os.system('cls' if os.name == 'nt' else 'clear')

    # Load environment variables from .env
    load_dotenv()

    # Load the helpdesk issues data file
    script_dir = Path(__file__).parent
    file_path = script_dir / 'tickets.txt'
    with file_path.open('r') as file:
        data = file.read() + "\n"

    # Ask for a prompt
    user_prompt = input(
        f"Here are the reported IT issues in your file:\n\n{data}\n\n"
        f"What would you like me to do with them? [default: Create a ticket for my issue]\n\n"
    )
    if not user_prompt:
        user_prompt = "Create a ticket for my issue"

    try:
        await process_helpdesk_issues(user_prompt, data)
    except (asyncio.CancelledError, Exception):
        pass


async def process_helpdesk_issues(prompt, issues_data):

    # Create a client and initialize an agent with the tool and instructions
    credential = AzureCliCredential()
    async with (
        Agent(
            client=AzureOpenAIResponsesClient(
                credential=credential,
                deployment_name=os.getenv("MODEL_DEPLOYMENT_NAME"),
                project_endpoint=os.getenv("PROJECT_ENDPOINT"),
            ),
            instructions="""You are an AI assistant for an IT helpdesk.
                        At the user's request, read the reported IT issue and use the plug-in function
                        to create a support ticket. Choose an appropriate category
                        (for example: Hardware, Software, Network, Account, or Security),
                        set a priority of Low, Medium, High, or Critical based on the impact described,
                        and write a concise summary of the problem.
                        Then confirm to the user that you've created the ticket.
                        Don't ask for any more information from the user, just use the data provided
                        to create the ticket.""",
            tools=[create_ticket],
        ) as agent,
    ):

        # Use the agent to process the helpdesk issues
        try:
            # Add the input prompt to a list of messages to be submitted
            prompt_messages = [f"{prompt}: {issues_data}"]
            # Invoke the agent for the specified thread with the messages
            response = await agent.run(prompt_messages)
            # Display the response
            print(f"\n# Agent:\n{response}")
        except Exception as e:
            # Something went wrong
            print(e)


# Create a tool function for the ticket functionality
@tool(approval_mode="never_require")
def create_ticket(
    category: Annotated[str, Field(description="The category of the issue, e.g. Hardware, Software, Network, Account, or Security.")],
    priority: Annotated[str, Field(description="The priority of the ticket: Low, Medium, High, or Critical.")],
    summary: Annotated[str, Field(description="A concise summary of the reported issue.")]):
        print("\nCategory:", category)
        print("Priority:", priority)
        print("Summary:", summary, "\n")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nInterrupted.")
