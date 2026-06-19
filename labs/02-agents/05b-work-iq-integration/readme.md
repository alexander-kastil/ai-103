# Work IQ - Workplace intelligence for AI agents

In this lab, you'll build an AI agent that accesses your Microsoft 365 workplace data using **Work IQ** - Microsoft's contextual intelligence layer built on the Model Context Protocol (MCP). You'll create a workplace intelligence agent that can prepare for meetings, track projects, extract action items, and answer workplace questions using real M365 data.

This lab takes approximately **40** minutes.

> **Note:** This is an **optional/advanced lab** that requires a Microsoft 365 Copilot license. It's designed for enterprise learners, Microsoft employees, or those with M365 Copilot access. Standard M365 accounts without Copilot will not work.

## Prerequisites

Before starting this lab, ensure you have:

- Basic understanding of AI agents and the Model Context Protocol (MCP)
- **Microsoft 365 with Copilot License**
- IT admin approval for Work IQ (organizational accounts only)
- [Node.js 18](https://nodejs.org/en/download/) or later installed
- [Python 3.13](https://www.python.org/downloads/) or later installed
- [Azure CLI](https://learn.microsoft.com/cli/azure/install-azure-cli) installed (authenticated with `az login`)
- Active M365 data (emails, meetings, Teams chats) to query

> **Important:** Work IQ **only works** with Microsoft 365 Copilot-enabled accounts. You cannot complete this lab without Copilot.

## Install Work IQ

1. Open your terminal or command prompt.

2. Install Work IQ globally via npm:

   ```bash
   npm install -g @microsoft/workiq
   ```

3. Accept the End User License Agreement:

   ```bash
   workiq accept-eula
   ```

4. Test your Work IQ installation:

   ```bash
   workiq ask -q "What meetings do I have today?"
   ```

5. **If the test succeeds** - You'll see meeting information from your M365 calendar. Continue to the next task!

6. **If you see "Admin consent required":**

   - The command will display a consent URL
   - Send this URL to your IT administrator with the message: "I need Work IQ access for the Microsoft Learn AI Agents lab"
   - Wait for admin approval, then retry the test command

7. **If you see "No M365 Copilot license":**

   - Unfortunately, you cannot complete this lab without a Copilot license
   - You can still read through the instructions to understand the concepts
   - Consider this lab optional and return to it when you have Copilot access

## Prepare to develop an app in Visual Studio Code

Now let's use Visual Studio Code to develop an app. The starter code is in the **Python** folder of this lab.

1. Start Visual Studio Code, and open the **Python** folder of this lab.

2. In the terminal, enter the command to create a Python virtual environment:

   ```bash
   python -m venv venv
   ```

3. Activate the virtual environment:

   **Windows:**

   ```bash
   venv\Scripts\activate
   ```

   **macOS/Linux:**

   ```bash
   source venv/bin/activate
   ```

4. Install required Python packages:

   ```bash
   pip install -r requirements.txt
   ```

5. Configure your `.env` file:

   In the Python folder, open the `.env` file and update it with your Foundry project endpoint:

   ```env
   PROJECT_ENDPOINT=https://your-project.services.ai.azure.com/api/projects/your-id
   MODEL_DEPLOYMENT_NAME=gpt-4.1
   ```

   > **Tip:** To get your endpoint: In VS Code, open the **Foundry Toolkit** extension, right-click on your active project, and select **Copy Endpoint**.

### Verify setup

Ensure you have:

- Work IQ installed and accessible (`workiq --version` works)
- Admin consent approved (or personal M365 account with Copilot)
- `workiq_lab.py` - Main interactive application
- `requirements.txt` - Python dependencies installed
- `.env` file configured with your project endpoint

## Explore Workplace Intelligence Scenarios

In this exercise, you'll run a unified interactive application that demonstrates five workplace intelligence scenarios using a single AI agent with Work IQ tools.

### Launch the lab application

1. Ensure you're in the Python directory with your virtual environment activated.

2. Run the lab application:

   ```bash
   python workiq_lab.py
   ```

3. The application will:
   - Validate Work IQ setup
   - Connect to your Microsoft Foundry project
   - Initialize the Work IQ MCP client
   - Create a workplace intelligence agent
   - Display an interactive menu with 5 scenarios

### Meeting Prep scenario

This scenario helps you prepare for meetings by gathering relevant context.

1. From the main menu, select **1 - Meeting Prep**.

2. When prompted, enter a meeting topic or time, such as:
   - "my 2pm meeting"
   - "Q4 Planning session"
   - "team standup"

3. The agent will:
   - Find your meeting details (time, attendees, agenda)
   - Search recent emails about the topic
   - Look for previous meetings on this subject
   - Summarize key points and decisions
   - Suggest discussion points

4. Review the output and note:
   - How sources are cited (emails, meetings, dates)
   - How the agent synthesizes information from multiple sources
   - The time saved compared to manual searching

**Reflection:** How does this differ from manually searching your email and calendar?

### Project Status scenario

This scenario tracks project updates across your workplace tools.

1. From the main menu, select **2 - Project Status**.

2. Enter a project name you're working on, such as:
   - "Website redesign"
   - "Q1 OKRs"
   - "Customer onboarding"

3. The agent will:
   - Search emails and Teams messages about the project
   - Find related meetings and their outcomes
   - Identify recent decisions and changes
   - List blockers or issues mentioned
   - Summarize next steps and deadlines

### Action Items scenario

This scenario extracts your open tasks from various sources.

1. From the main menu, select **3 - Action Items**.

2. Choose a time range (or press Enter for "this week"):
   - "today"
   - "last 3 days"
   - "this month"

3. The agent will:
   - Search meeting notes for assigned action items
   - Look for task-related emails sent to you
   - Check Teams messages where you were mentioned
   - Identify items with deadlines
   - Prioritize by urgency if possible

### Combined Intelligence scenario

This scenario demonstrates using **both** Work IQ (workplace data) and Foundry IQ (knowledge base) together.

> **Note:** This scenario requires Azure AI Search configured in your Foundry project with an indexed knowledge base.

1. From the main menu, select **4 - Combined Intelligence**.

2. Enter a topic that exists in both your workplace discussions and official documentation:
   - "remote work policy"
   - "expense reporting"
   - "security guidelines"

3. The agent will:
   - Search workplace data (Work IQ): emails, meetings, Teams discussions
   - Search knowledge base (Foundry IQ): official docs, policies, procedures
   - Compare workplace discussions with official documentation
   - Identify gaps or inconsistencies
   - Provide a comprehensive summary with labeled sources

**Key Insight:**

- **Work IQ** tells you what people are actually doing and saying
- **Foundry IQ** tells you what's officially documented
- **Together** they provide complete context for decision-making

### Custom Query scenario

This scenario lets you explore your workplace data with your own questions.

1. From the main menu, select **5 - Custom Query**.

2. Try different types of workplace questions:

   **Email searches:**

   ```
   Find emails about the budget from my manager
   ```

   **Meeting summaries:**

   ```
   What was decided in yesterday's standup?
   ```

   **Team activity:**

   ```
   What did the engineering team discuss this week?
   ```

   **Document discovery:**

   ```
   Show me shared documents about security policies
   ```

## Understanding the Code

Let's examine the key patterns used in this lab.

### Pattern 1: Work IQ MCP Client Initialization

```python
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

# Store server parameters for reuse
self.workiq_server_params = StdioServerParameters(
    command="npx",
    args=["-y", "@microsoft/workiq", "mcp"]
)

# Fetch available tools from Work IQ MCP server
async def _fetch():
    async with stdio_client(self.workiq_server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            tools_result = await session.list_tools()
            return tools_result.tools

raw_tools = asyncio.run(_fetch())
```

### Pattern 2: Creating Agent with Work IQ Tools

```python
from azure.ai.projects.models import PromptAgentDefinition, FunctionTool

# Convert MCP tools to FunctionTool objects
workiq_tools = [
    FunctionTool(
        name=tool.name,
        description=tool.description,
        parameters=tool.inputSchema,
    )
    for tool in raw_tools
]

# Create agent with Work IQ tools
self.agent = self.project_client.agents.create_version(
    agent_name="workplace-intelligence-agent",
    definition=PromptAgentDefinition(
        model=self.model_deployment,
        instructions="You are a workplace intelligence assistant...",
        tools=workiq_tools
    )
)
```

### Pattern 3: Tool Call Loop

```python
from openai.types.responses.response_input_param import FunctionCallOutput

while True:
    if response.status == "failed":
        break

    input_list = []
    for item in response.output:
        if item.type == "function_call":
            kwargs = json.loads(item.arguments)

            async def _execute():
                async with stdio_client(self.workiq_server_params) as (read, write):
                    async with ClientSession(read, write) as session:
                        await session.initialize()
                        return await session.call_tool(item.name, kwargs)

            result = asyncio.run(_execute())
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
            extra_body={"agent_reference": {"name": self.agent.name, "type": "agent_reference"}}
        )
    else:
        break
```

## Clean Up

The lab automatically cleans up the agent when you exit. No Azure resources are created in this lab (Work IQ uses your M365 license), so no additional cleanup is needed.

## Troubleshooting

### "Work IQ command not found"

**Solution:** Install Work IQ:

```bash
npm install -g @microsoft/workiq
```

### "Admin consent required"

**Solution:**

1. Run `workiq mcp` to get the consent URL
2. Send to your IT admin for approval
3. Or use a personal M365 account with Copilot

### "No M365 Copilot license"

**Solution:** This lab requires Copilot. Either:

- Purchase M365 Copilot license ($30/month)
- Use organizational account with Copilot
- Read through the lab to understand concepts without hands-on

### "MCP server not responding"

**Solution:** Test Work IQ directly:

```bash
workiq ask -q "What meetings do I have?"
```

If this fails, reinstall:

```bash
npm install -g @microsoft/workiq
```

### "No data returned"

**Solution:**

- Ensure your M365 account has emails, meetings, Teams activity
- Try broader queries
- Check if your query matches your actual data
