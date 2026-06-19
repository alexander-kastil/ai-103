""" Microsoft Foundry prompt agent that generates a title """

import os

from azure.ai.projects import AIProjectClient
from azure.ai.projects.models import PromptAgentDefinition
from azure.identity import DefaultAzureCredential


class TitleAgent:

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

        # Create the title agent
        self.agent = self.project.agents.create_version(
            agent_name='title-agent',
            definition=PromptAgentDefinition(
                model=os.environ['MODEL_DEPLOYMENT_NAME'],
                instructions="""
                You are a helpful writing assistant.
                Given a topic the user wants to write about, suggest a single clear and catchy blog post title.
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


async def create_foundry_title_agent() -> TitleAgent:
    agent = TitleAgent()
    await agent.create_agent()
    return agent
