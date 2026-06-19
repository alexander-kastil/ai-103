""" Microsoft Foundry prompt agent that proposes catchy podcast episode titles """

import os
from azure.ai.projects import AIProjectClient
from azure.ai.projects.models import PromptAgentDefinition
from azure.identity import DefaultAzureCredential

class TitleAgent:

    def __init__(self):

        self.project = AIProjectClient(
            endpoint=os.environ['PROJECT_ENDPOINT'],
            credential=DefaultAzureCredential(
                exclude_environment_credential=True,
                exclude_managed_identity_credential=True
            )
        )
        self.openai = self.project.get_openai_client()
        self.agent_name = 'podcast-title-agent'
        self.agent = None

    async def create_agent(self):
        if self.agent:
            return self.agent

        self.agent = self.project.agents.create_version(
            agent_name=self.agent_name,
            definition=PromptAgentDefinition(
                model=os.environ['MODEL_DEPLOYMENT_NAME'],
                instructions="""
                You are a helpful podcast production assistant.
                Given a topic the user wants to cover in an episode, suggest a single clear and catchy podcast episode title.
                Keep it punchy and listener-friendly, ideally under 10 words.
                """,
            ),
        )

        return self.agent

    async def run_conversation(self, user_message: str) -> list[str]:

        if not self.agent:
            await self.create_agent()

        response = self.openai.responses.create(
            input=user_message,
            extra_body={"agent_reference": {"name": self.agent_name, "type": "agent_reference"}},
        )

        return [response.output_text] if response.output_text else ['No response received']

async def create_foundry_title_agent() -> TitleAgent:
    agent = TitleAgent()
    await agent.create_agent()
    return agent
