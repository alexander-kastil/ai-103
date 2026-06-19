""" Microsoft Foundry prompt agent that generates an outline """

import os

from azure.ai.projects import AIProjectClient
from azure.ai.projects.models import PromptAgentDefinition
from azure.identity import DefaultAzureCredential


class OutlineAgent:

    def __init__(self):

        # Create the project client
        self.project = AIProjectClient(
            endpoint=os.environ['PROJECT_ENDPOINT'],
            credential=DefaultAzureCredential(
                exclude_environment_credential=True,
                exclude_managed_identity_credential=True
            )
        )
        self.openai = self.project.get_openai_client()
        self.agent = None

    async def create_agent(self):
        if self.agent:
            return self.agent

        # Create the outline agent
        self.agent = self.project.agents.create_version(
            agent_name='outline-agent',
            definition=PromptAgentDefinition(
                model=os.environ['MODEL_DEPLOYMENT_NAME'],
                instructions="""
                You are a helpful writing assistant.
                Based on the provided title or topic, write a concise outline with 4 to 6 key sections.
                Each section should be 5 to 10 words long, suitable for structuring a short blog post.
                """,
            ),
        )
        return self.agent

    async def run_conversation(self, user_message: str) -> list[str]:
        if not self.agent:
            await self.create_agent()

        # Create a conversation for the chat session
        conversation = self.openai.conversations.create()

        # Send the user message and run the agent
        response = self.openai.responses.create(
            input=user_message,
            conversation=conversation.id,
            extra_body={'agent_reference': {'name': self.agent.name, 'type': 'agent_reference'}},
        )

        # Get the agent's text response
        return [response.output_text] if response.output_text else ['No response received']


async def create_foundry_outline_agent() -> OutlineAgent:
    agent = OutlineAgent()
    await agent.create_agent()
    return agent
