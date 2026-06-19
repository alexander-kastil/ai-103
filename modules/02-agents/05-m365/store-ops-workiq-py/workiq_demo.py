"""
Work IQ demo — Store Operations Intelligence (Contoso Retail)

This demo shows how to extend the base store-ops-assistant agent with live
Microsoft 365 workplace data (emails, calendar, Teams messages, shared documents)
through Work IQ, the Model Context Protocol (MCP) server for Microsoft 365 Copilot.

The base agent (store-ops-assistant) provides file-search grounding over the four
store-operations documents. This demo creates a new version of that agent that also
includes Work IQ MCP tools so the agent can access live M365 data alongside the
grounding documents.

Scenarios:
  1. Store-Ops Email Digest - summarize this week's store-operations emails
  2. District Sync Prep      - gather context for the district managers meeting
  3. Action Items            - extract open tasks from emails and meetings
  4. Custom Query            - ask your own store-operations question

Requires a Microsoft 365 Copilot license and Work IQ installed:
  npm install -g @microsoft/workiq
  workiq accept-eula
"""

import os
import json
import asyncio

from dotenv import load_dotenv
from azure.ai.projects import AIProjectClient
from azure.ai.projects.models import FileSearchTool, FunctionTool, PromptAgentDefinition
from azure.identity import DefaultAzureCredential
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from openai.types.responses.response_input_param import FunctionCallOutput, ResponseInputParam

os.system('cls' if os.name == 'nt' else 'clear')

load_dotenv(override=True)

BASE_AGENT_NAME = "store-ops-assistant"
VECTOR_STORE_NAME = "store-ops-index"

WORKIQ_INSTRUCTIONS_SUFFIX = """

You also have access to live Microsoft 365 data through Work IQ tools:
emails, calendar meetings, Teams channel messages, and SharePoint documents.
Use these tools to answer questions about current store-operations communications.
Always cite sources with timestamps when referencing live M365 data.
Respect existing M365 permissions — you only surface data the user can already access.
"""


class StoreOpsWorkIQDemo:
    def __init__(self):
        self.project_endpoint = os.getenv("PROJECT_ENDPOINT")
        self.model_deployment = os.getenv("MODEL_DEPLOYMENT_NAME", "gpt-5.4")

        if not self.project_endpoint:
            print("Error: PROJECT_ENDPOINT not set in .env file")
            print("Copy .env.example to .env and set your Microsoft Foundry project endpoint")
            exit(1)

        print("Connecting to Microsoft Foundry project...")
        self.credential = DefaultAzureCredential(
            exclude_environment_credential=True,
            exclude_managed_identity_credential=True,
            exclude_shared_token_cache_credential=True,
        )
        self.project_client = None
        self.openai_client = None
        self.agent_version = None
        self.workiq_server_params = None

    def validate_workiq_setup(self):
        import subprocess

        print("\n" + "=" * 70)
        print("VALIDATING WORK IQ SETUP")
        print("=" * 70)

        result = subprocess.run(
            ["workiq", "--version"],
            capture_output=True,
            text=True,
            timeout=10,
            shell=True,
        )

        if result.returncode == 0:
            print("Work IQ is installed")
            print(f"   Version: {result.stdout.strip()}\n")
            return True

        print("Work IQ not found or not working properly")
        print("\nTo install Work IQ:")
        print("   npm install -g @microsoft/workiq")
        print("   workiq accept-eula\n")
        return False

    def connect(self):
        if not self.validate_workiq_setup():
            print("Warning: Work IQ validation failed, but continuing...")
            print("   Make sure Work IQ is installed and configured.\n")

        self.project_client = AIProjectClient(
            credential=self.credential,
            endpoint=self.project_endpoint,
        )
        self.openai_client = self.project_client.get_openai_client()

        print("Connecting to Work IQ MCP server...")
        self.workiq_server_params = StdioServerParameters(
            command="npx",
            args=["-y", "@microsoft/workiq", "mcp"],
        )

        print("Connected to Microsoft Foundry and Work IQ MCP\n")
        self._create_unified_version()
        return True

    def _resolve_vector_store_id(self):
        for vs in self.openai_client.vector_stores.list():
            if vs.name == VECTOR_STORE_NAME:
                return vs.id
        raise RuntimeError(
            f"Vector store '{VECTOR_STORE_NAME}' not found. "
            "Run store-ops-agent-py/provision-agent.py first."
        )

    def _get_base_agent_instructions(self):
        agents = list(self.project_client.agents.list())
        for a in agents:
            if a.name == BASE_AGENT_NAME:
                versions = list(self.project_client.agents.list_versions(BASE_AGENT_NAME))
                if versions:
                    return versions[0].definition.instructions
        raise RuntimeError(
            f"Base agent '{BASE_AGENT_NAME}' not found. "
            "Run store-ops-agent-py/provision-agent.py first."
        )

    def _get_workiq_tools(self):
        async def _fetch():
            async with stdio_client(self.workiq_server_params) as (read, write):
                async with ClientSession(read, write) as session:
                    await session.initialize()
                    tools_result = await session.list_tools()
                    return tools_result.tools
        return asyncio.run(_fetch())

    def _call_workiq_tool(self, tool_name, kwargs):
        async def _execute():
            async with stdio_client(self.workiq_server_params) as (read, write):
                async with ClientSession(read, write) as session:
                    await session.initialize()
                    return await session.call_tool(tool_name, kwargs)
        return asyncio.run(_execute())

    def _create_unified_version(self):
        print(f"Resolving '{VECTOR_STORE_NAME}' vector store...")
        vector_store_id = self._resolve_vector_store_id()
        print(f"   Vector store id: {vector_store_id}")

        print(f"Fetching base instructions from '{BASE_AGENT_NAME}'...")
        base_instructions = self._get_base_agent_instructions()

        print("Fetching Work IQ MCP tools...")
        raw_tools = self._get_workiq_tools()
        workiq_tools = [
            FunctionTool(
                name=tool.name,
                description=tool.description,
                parameters=tool.inputSchema,
            )
            for tool in raw_tools
        ]
        print(f"   Work IQ tools: {len(workiq_tools)}")

        instructions = base_instructions + WORKIQ_INSTRUCTIONS_SUFFIX

        print(f"Creating new version of '{BASE_AGENT_NAME}' with file-search + Work IQ tools...")
        self.agent_version = self.project_client.agents.create_version(
            agent_name=BASE_AGENT_NAME,
            definition=PromptAgentDefinition(
                model=self.model_deployment,
                instructions=instructions,
                tools=[FileSearchTool(vector_store_ids=[vector_store_id])] + workiq_tools,
            ),
        )

        print(f"Agent version created: {self.agent_version.name} (version {self.agent_version.version})\n")

    def _execute_query(self, query, scenario_name="Query"):
        print(f"\n{'=' * 70}")
        print(f"{scenario_name}")
        print(f"{'=' * 70}")
        print(f"\nQuery: {query}\n")
        print("Processing with Work IQ tools...")

        conversation = self.openai_client.conversations.create(
            items=[{"type": "message", "role": "user", "content": query}]
        )

        response = self.openai_client.responses.create(
            conversation=conversation.id,
            extra_body={"agent_reference": {"name": self.agent_version.name, "type": "agent_reference"}},
        )

        while True:
            if response.status == "failed":
                print(f"Response failed: {response.error}")
                return

            input_list: ResponseInputParam = []

            for item in response.output:
                if item.type == "function_call":
                    function_name = item.name
                    kwargs = json.loads(item.arguments)

                    print(f"   [tool call] {function_name}({kwargs})")

                    result = self._call_workiq_tool(function_name, kwargs)

                    input_list.append(
                        FunctionCallOutput(
                            type="function_call_output",
                            call_id=item.call_id,
                            output=result.content[0].text,
                        )
                    )

            if input_list:
                response = self.openai_client.responses.create(
                    input=input_list,
                    previous_response_id=response.id,
                    extra_body={
                        "agent_reference": {"name": self.agent_version.name, "type": "agent_reference"}
                    },
                )
            else:
                break

        print("\nResponse:")
        print("-" * 70)
        if response.output_text:
            print(response.output_text)
        else:
            print("No response received from agent.")
        print("-" * 70)

    def scenario_email_digest(self):
        query = """Summarize this week's store-operations emails. Please:
1. Find emails about store operations: POS issues, returns, inventory, staffing, promotions
2. Group them by theme
3. Call out anything urgent or with a deadline
4. List who I should follow up with

Provide a concise digest with sources and dates."""
        self._execute_query(query, "Store-Ops Email Digest")

    def scenario_district_sync_prep(self):
        meeting = input(
            "Enter the meeting topic or time [default: the district managers sync]: "
        ).strip() or "the district managers sync"

        query = f"""Help me prepare for {meeting}. Please:
1. Find the meeting details (time, attendees, agenda)
2. Search recent emails and Teams messages about store operations
3. Look for previous meetings on this topic and their decisions
4. Summarize the key store-ops points I should be ready to discuss
5. Suggest questions or updates to raise

Provide a concise prep summary with sources."""
        self._execute_query(query, "District Sync Prep")

    def scenario_action_items(self):
        time_filter = input(
            "Time range [default: the past week]: "
        ).strip() or "the past week"

        query = f"""Find my open store-operations action items from {time_filter}. Please:
1. Search meeting notes for assigned action items
2. Look for task-related emails sent to me
3. Check Teams messages where I was mentioned or assigned a task
4. Identify items with deadlines
5. Prioritize by urgency

Provide a prioritized list with sources, deadlines, and who assigned each item."""
        self._execute_query(query, "Action Items")

    def scenario_custom_query(self):
        print("\nAsk any store-operations question. Examples:")
        print("  - What did the regional manager say about the new returns policy?")
        print("  - Find emails about the POS outage last Friday")
        print("  - Summarize this week's store-ops Teams thread")
        print("  - What did we decide about holiday staffing?\n")

        custom_query = input("Your store-operations question: ").strip()
        if not custom_query:
            print("\nNo query entered. Returning to menu.")
            return

        self._execute_query(custom_query, "Custom Query")

    def show_menu(self):
        print("\n" + "=" * 70)
        print("   WORK IQ DEMO — STORE OPERATIONS INTELLIGENCE (CONTOSO RETAIL)")
        print("=" * 70)
        print("\nChoose a scenario:\n")
        print("  1. Store-Ops Email Digest  - summarize this week's store-ops emails")
        print("  2. District Sync Prep      - prep for the district managers meeting")
        print("  3. Action Items            - extract open tasks from emails/meetings")
        print("  4. Custom Query            - ask your own store-ops question")
        print("  0. Exit")
        print("\n" + "=" * 70)

    def run(self):
        print("\n" + "=" * 70)
        print("   WORK IQ DEMO — STORE OPERATIONS INTELLIGENCE FOR AI AGENTS")
        print("=" * 70)
        print("\nThis demo extends store-ops-assistant with live Microsoft 365 data")
        print("(emails, meetings, Teams) using Work IQ alongside the store-ops grounding documents.\n")

        try:
            self.connect()
        except (KeyboardInterrupt, asyncio.CancelledError):
            print("\nInterrupted during setup.")
            return

        try:
            while True:
                self.show_menu()
                choice = input("\nSelect option (0-4) [default: 1]: ").strip()
                if not choice:
                    choice = "1"

                if choice == "1":
                    self.scenario_email_digest()
                elif choice == "2":
                    self.scenario_district_sync_prep()
                elif choice == "3":
                    self.scenario_action_items()
                elif choice == "4":
                    self.scenario_custom_query()
                elif choice == "0":
                    print("\nExiting demo...")
                    break
                else:
                    print("\nInvalid option. Please choose 0-4.")

                input("\nPress Enter to continue...")

        except (KeyboardInterrupt, asyncio.CancelledError):
            print("\nInterrupted.")

        print("\nDemo complete.\n")


if __name__ == "__main__":
    demo = StoreOpsWorkIQDemo()
    demo.run()
