""" Routing (host) agent that discovers the remote podcast agents and delegates work """

import asyncio
import json
import os
import uuid
import httpx

from typing import Any, Callable
from azure.ai.projects import AIProjectClient
from azure.ai.projects.models import PromptAgentDefinition, FunctionTool
from azure.identity import DefaultAzureCredential
from collections.abc import Callable
from dotenv import load_dotenv
from openai.types.responses.response_input_param import FunctionCallOutput, ResponseInputParam
from a2a.client import A2ACardResolver, A2AClient
from a2a.types import (
    AgentCard,
    MessageSendParams,
    SendMessageRequest,
    SendMessageResponse,
    SendMessageSuccessResponse,
    Task,
    TaskArtifactUpdateEvent,
    TaskStatusUpdateEvent,
)

load_dotenv()

TaskCallbackArg = Task | TaskStatusUpdateEvent | TaskArtifactUpdateEvent
TaskUpdateCallback = Callable[[TaskCallbackArg, AgentCard], Task]


class RemoteAgentConnections:
    """A class to hold the connections to the remote agents."""

    def __init__(self, agent_card: AgentCard, agent_url: str):
        self._httpx_client = httpx.AsyncClient(timeout=30)
        self.agent_client = A2AClient(self._httpx_client, agent_card, url=agent_url)
        self.card = agent_card

    def get_agent(self) -> AgentCard:
        return self.card

    async def send_message(self, message_request: SendMessageRequest) -> SendMessageResponse:
        return await self.agent_client.send_message(message_request)

class RoutingAgent:

    def __init__(self, task_callback: TaskUpdateCallback | None = None):

        self.task_callback = task_callback
        self.remote_agent_connections: dict[str, RemoteAgentConnections] = {}
        self.cards: dict[str, AgentCard] = {}
        self.agents: str = ''

        self.project = AIProjectClient(
            endpoint=os.environ["PROJECT_ENDPOINT"],
            credential=DefaultAzureCredential(
                exclude_environment_credential=True,
                exclude_managed_identity_credential=True
            )
        )
        self.openai = self.project.get_openai_client()

        self.agent_name = "podcast-routing-agent"
        self.azure_agent = None
        self.conversation = None


    @classmethod
    async def create(cls, remote_agent_addresses: list[str], task_callback: TaskUpdateCallback | None = None) -> 'RoutingAgent':
        """Create and asynchronously initialize an instance of the RoutingAgent."""
        instance = cls(task_callback)
        await instance._async_init_components(remote_agent_addresses)
        return instance


    def list_remote_agents(self) -> str:
        if not self.remote_agent_connections:
            return "[]"

        lines = []
        for card in self.cards.values():
            lines.append(f"{card.name}: {card.description}")

        return "[\n  " + ",\n  ".join(lines) + "\n]"


    async def _async_init_components(self, remote_agent_addresses: list[str]) -> None:
        """Asynchronous part of initialization."""

        # Use a single httpx.AsyncClient for all card resolutions for efficiency
        async with httpx.AsyncClient(timeout=30) as client:
            for address in remote_agent_addresses:
                card_resolver = A2ACardResolver(client, address)
                try:
                    card = await card_resolver.get_agent_card()

                    remote_connection = RemoteAgentConnections(agent_card=card, agent_url=address)
                    self.remote_agent_connections[card.name] = remote_connection
                    self.cards[card.name] = card

                except httpx.ConnectError as e:
                    print(f'ERROR: Failed to get agent card from {address}: {e}')
                except Exception as e:  # Catch other potential errors
                    print(f'ERROR: Failed to initialize connection for {address}: {e}')
            print(f"Found remote agents: {self.list_remote_agents()}")


    async def send_message(self, agent_name: str, task: str):
        # Sends a task to remote agent.

        if agent_name not in self.remote_agent_connections:
            raise ValueError(f'Agent {agent_name} not found')

        # Retrieve the remote agent's A2A client using the agent name
        client = self.remote_agent_connections[agent_name]

        if not client:
            raise ValueError(f'Client not available for {agent_name}')

        message_id = str(uuid.uuid4())

        # Construct the payload to send to the remote agent
        payload: dict[str, Any] = {
            'message': {
                'role': 'user',
                'parts': [{'kind': 'text', 'text': task}],
                'messageId': message_id,
            },
        }

        # Wrap the payload in a SendMessageRequest object
        message_request = SendMessageRequest(id=message_id, params=MessageSendParams.model_validate(payload))

        # Send the message to the remote agent client and await the response
        send_response: SendMessageResponse = await client.send_message(message_request=message_request)

        if not isinstance(send_response.root, SendMessageSuccessResponse):
            print('received non-success response. Aborting get task ')
            return

        if not isinstance(send_response.root.result, Task):
            print('received non-task response. Aborting get task ')
            return

        return send_response.root.result


    def create_agent(self):
        # Create a Foundry prompt agent that exposes send_message as a function tool

        send_message_tool = FunctionTool(
            name="send_message",
            parameters={
                "type": "object",
                "properties": {
                    "agent_name": {
                        "type": "string",
                        "description": "The name of the remote agent to delegate the task to.",
                    },
                    "task": {
                        "type": "string",
                        "description": "The task description to send to the remote agent.",
                    },
                },
                "required": ["agent_name", "task"],
                "additionalProperties": False,
            },
            description="Delegate a task to a remote A2A agent by name and return its result.",
            strict=True,
        )

        self.azure_agent = self.project.agents.create_version(
            agent_name=self.agent_name,
            definition=PromptAgentDefinition(
                model=os.environ["ROUTING_MODEL_DEPLOYMENT_NAME"],
                instructions=f"""
                You are an expert Routing Delegator that helps users plan podcast episodes.

                Your role:
                - Delegate user inquiries to the appropriate specialized remote agents
                - Use the title agent to propose a catchy episode title
                - Use the segment agent to draft the episode segment breakdown
                - When a user asks for both a title and a segment breakdown, first get a title,
                  then pass that title to the segment agent so the segments match the title
                - Provide clear and helpful responses to users

                Available Agents: {self.list_remote_agents()}

                Always be helpful and route requests to the most appropriate agent.""",
                tools=[send_message_tool],
            ),
        )

        self.conversation = self.openai.conversations.create()

        return self.azure_agent

    async def process_user_message(self, user_message: str) -> str:

        if not self.azure_agent:
            return "Routing agent not initialized. Please ensure the agent is properly created."

        if not self.conversation:
            return "Conversation not initialized. Please ensure the agent is properly created."

        response = self.openai.responses.create(
            input=user_message,
            conversation=self.conversation.id,
            extra_body={"agent_reference": {"name": self.agent_name, "type": "agent_reference"}},
        )

        while True:
            input_list: ResponseInputParam = []

            for item in response.output:
                if item.type == "function_call" and item.name == "send_message":
                    function_args = json.loads(item.arguments)
                    result = await self.send_message(agent_name=function_args["agent_name"], task=function_args["task"])
                    output = json.dumps(result.model_dump() if hasattr(result, 'model_dump') else str(result))

                    input_list.append(
                        FunctionCallOutput(
                            type="function_call_output",
                            call_id=item.call_id,
                            output=output,
                        )
                    )

            if not input_list:
                break

            response = self.openai.responses.create(
                input=input_list,
                conversation=self.conversation.id,
                extra_body={"agent_reference": {"name": self.agent_name, "type": "agent_reference"}},
            )

        return response.output_text if response.output_text else "No response received from agent."


def _remote_agent_addresses() -> list[str]:
    server_url = os.environ["SERVER_URL"]
    title_port = os.environ["TITLE_AGENT_PORT"]
    segment_port = os.environ["SEGMENT_AGENT_PORT"]
    return [
        f"http://{server_url}:{title_port}",
        f"http://{server_url}:{segment_port}",
    ]


async def _get_initialized_routing_agent_sync() -> RoutingAgent:

    async def _async_main() -> RoutingAgent:
        routing_agent_instance = await RoutingAgent.create(
            remote_agent_addresses=_remote_agent_addresses()
        )
        # Create the Foundry prompt agent
        routing_agent_instance.create_agent()
        return routing_agent_instance

    try:
        return asyncio.run(_async_main())
    except RuntimeError:
        raise
