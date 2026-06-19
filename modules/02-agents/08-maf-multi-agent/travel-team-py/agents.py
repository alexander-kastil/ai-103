# Add references
import asyncio
import os
from pathlib import Path
from typing import cast
from dotenv import load_dotenv
from agent_framework import Message
from agent_framework.azure import AzureAIAgentClient
from agent_framework.orchestrations import SequentialBuilder
from azure.identity import AzureCliCredential

load_dotenv()


async def main():
    # Clear the console
    os.system('cls' if os.name == 'nt' else 'clear')

    # Agent instructions
    destination_researcher_instructions = """
    You are a destination researcher for a travel planning team.
    Given a traveller's request, recommend ONE specific destination that fits it.
    In 2-3 short sentences, name the destination and justify it with the climate,
    the best time to visit, and one signature highlight.
    Example output:
    Lisbon, Portugal. Mild Atlantic climate makes spring ideal, and the historic
    Alfama district offers iconic views and fado music.
    """

    budget_planner_instructions = """
    You are a budget planner for a travel planning team.
    Based on the recommended destination, produce a concise estimated budget
    for a 5-day trip for the party size implied by the request (assume 2 adults
    if unspecified). Break it down into Flights, Accommodation, Food, and Activities
    as bullet points with approximate amounts in USD, then give a Total.
    Keep numbers realistic and rounded. Do not add commentary beyond the budget.
    """

    itinerary_writer_instructions = """
    You are an itinerary writer for a travel planning team.
    Using the recommended destination and the estimated budget, write a friendly,
    well-structured 5-day itinerary. Provide one short paragraph per day (Day 1 to
    Day 5) covering morning, afternoon, and evening suggestions that respect the
    budget. End with a one-line packing tip.
    """

    # Create the chat client
    credential = AzureCliCredential()
    async with (
        AzureAIAgentClient(
            project_endpoint=os.getenv("PROJECT_ENDPOINT"),
            model_deployment_name=os.getenv("MODEL_DEPLOYMENT_NAME"),
            credential=credential,
        ) as chat_client,
    ):
        # Create agents
        destination_researcher = chat_client.as_agent(
            instructions=destination_researcher_instructions,
            name="destination_researcher",
        )

        budget_planner = chat_client.as_agent(
            instructions=budget_planner_instructions,
            name="budget_planner",
        )

        itinerary_writer = chat_client.as_agent(
            instructions=itinerary_writer_instructions,
            name="itinerary_writer",
        )

        # Initialize the current travel request
        request_path = Path(__file__).parent / "data" / "travel_request.txt"
        request = request_path.read_text(encoding="utf-8").strip()

        # Build sequential orchestration
        workflow = SequentialBuilder(
            participants=[destination_researcher, budget_planner, itinerary_writer]
        ).build()

        # Run and collect outputs
        outputs: list[list[Message]] = []
        try:
            async for event in workflow.run(f"Travel request: {request}", stream=True):
                if event.type == "output":
                    outputs.append(cast(list[Message], event.data))
        except (asyncio.CancelledError, Exception):
            pass

        # Display outputs
        if outputs:
            for i, msg in enumerate(outputs[-1], start=1):
                name = msg.author_name or ("assistant" if msg.role == "assistant" else "user")
                print(f"{'-' * 60}\n{i:02d} [{name}]\n{msg.text}")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nInterrupted.")
