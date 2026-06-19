import asyncio
import json
import os
import uuid
import httpx

from typing import Any
from azure.ai.projects import AIProjectClient
from azure.ai.projects.models import PromptAgentDefinition, FunctionTool
from azure.identity import DefaultAzureCredential
from openai.types.responses.response_input_param import FunctionCallOutput, ResponseInputParam
from collections.abc import Callable
from dotenv import load_dotenv
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

    def __init__(self,task_callback: TaskUpdateCallback | None = None):

        self.task_callback = task_callback
        self.remote_agent_connections: dict[str, RemoteAgentConnections] = {}
        self.cards: dict[str, AgentCard] = {}
        self.agents: str = ''

        # Initialize the Foundry project and OpenAI clients
        self.project = AIProjectClient(
            endpoint=os.environ["PROJECT_ENDPOINT"],
            credential=DefaultAzureCredential(
                exclude_environment_credential=True,
                exclude_managed_identity_credential=True
            )
        )
        self.openai = self.project.get_openai_client()

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
                    print( f'ERROR: Failed to get agent card from {address}: {e}')
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
        # Create a Microsoft Foundry prompt agent with the send_message function tool

        send_message_tool = FunctionTool(
            name="send_message",
            description="Delegate a task to a remote agent and return its response.",
            parameters={
                "type": "object",
                "properties": {
                    "agent_name": {
                        "type": "string",
                        "description": "The name of the remote agent to send the task to.",
                    },
                    "task": {
                        "type": "string",
                        "description": "The task or message to send to the remote agent.",
                    },
                },
                "required": ["agent_name", "task"],
                "additionalProperties": False,
            },
            strict=True,
        )

        self.azure_agent = self.project.agents.create_version(
            agent_name="routing-agent",
            definition=PromptAgentDefinition(
                model=os.environ["ROUTING_MODEL_DEPLOYMENT_NAME"],
                instructions=f"""
                You are an expert Routing Delegator that helps users with requests.

                Your role:
                - Delegate user inquiries to appropriate specialized remote agents
                - Provide clear and helpful responses to users

                Available Agents: {self.list_remote_agents()}

                Always be helpful and route requests to the most appropriate agent.""",
                tools=[send_message_tool],
            ),
        )

        # Create a conversation for the chat session
        self.conversation = self.openai.conversations.create()

        return self.azure_agent

    async def process_user_message(self, user_message: str) -> str:

        if not self.azure_agent:
            return "Foundry agent not initialized. Please ensure the agent is properly created."

        if not self.conversation:
            return "Conversation not initialized. Please ensure the agent is properly created."

        agent_reference = {'agent_reference': {'name': self.azure_agent.name, 'type': 'agent_reference'}}

        # Send the user message and run the agent
        response = self.openai.responses.create(
            input=user_message,
            conversation=self.conversation.id,
            extra_body=agent_reference,
        )

        # Resolve function calls until the agent returns a final answer
        while True:
            tool_outputs: ResponseInputParam = []

            for item in response.output:
                if item.type == "function_call" and item.name == "send_message":
                    function_args = json.loads(item.arguments)
                    result = await self.send_message(
                        agent_name=function_args["agent_name"], task=function_args["task"]
                    )
                    output = json.dumps(result.model_dump() if hasattr(result, 'model_dump') else str(result))
                    tool_outputs.append(
                        FunctionCallOutput(
                            type="function_call_output",
                            call_id=item.call_id,
                            output=output,
                        )
                    )

            if not tool_outputs:
                break

            response = self.openai.responses.create(
                input=tool_outputs,
                conversation=self.conversation.id,
                extra_body=agent_reference,
            )

        return response.output_text or "No response received from agent."


async def _get_initialized_routing_agent_sync() -> RoutingAgent:

    async def _async_main() -> RoutingAgent:
        routing_agent_instance = await RoutingAgent.create(
            remote_agent_addresses=[
                f"http://{os.environ["SERVER_URL"]}:{os.environ["TITLE_AGENT_PORT"]}",
                f"http://{os.environ["SERVER_URL"]}:{os.environ["OUTLINE_AGENT_PORT"]}",
            ]
        )
        # Create the Foundry prompt agent
        routing_agent_instance.create_agent()
        return routing_agent_instance

    try:
        return asyncio.run(_async_main())
    except RuntimeError as e:
        raise

# Initialize the routing agent
routing_agent = _get_initialized_routing_agent_sync()
