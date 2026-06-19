# Integrate an AI agent with Foundry IQ

In this exercise, you'll use Microsoft Foundry portal to create an agent that integrates with Foundry IQ to search and retrieve information from knowledge bases. You'll create a search resource, configure a knowledge base with sample data, build an agent in the portal, and then connect to it from Visual Studio Code to interact programmatically.

> **Tip**: The code used in this exercise is based on the Microsoft Foundry SDK for Python. You can develop similar solutions using the SDKs for Microsoft .NET, JavaScript, and Java. Refer to [Microsoft Foundry SDK client libraries](https://learn.microsoft.com/azure/ai-foundry/how-to/develop/sdk-overview) for details.

This exercise should take approximately **45** minutes to complete.

> **Note**: Some of the technologies used in this exercise are in preview or in active development. You may experience some unexpected behavior, warnings, or errors.

## Prerequisites

Before starting this exercise, ensure you have:

- An [Azure subscription](https://azure.microsoft.com/free/) with permissions to create AI resources
- [Visual Studio Code](https://code.visualstudio.com/) installed on your local machine
- [Python 3.13](https://www.python.org/downloads/) or later installed
- [Git](https://git-scm.com/downloads) installed on your local machine
- Basic familiarity with the Microsoft Foundry portal and Python programming

## Create a Foundry project

Let's start by creating a Foundry project with the new Foundry experience.

1. In a web browser, open the [Foundry portal](https://ai.azure.com) at `https://ai.azure.com` and sign in using your Azure credentials. Close any tips or quick start panes that are opened the first time you sign in.

    > **Important**: Make sure the **New Foundry** toggle is *On* for this lab to use the updated user interface.

1. Once you toggle to the **New Foundry**, you'll be asked to select a project. In the dropdown, select **Create a new project**.
1. In the **Create a project** dialog, enter a valid name for your project (for example, *agent-iq-lab*).
1. Confirm or configure the following settings for your project:
    - **Foundry resource**: *Create a new Foundry resource or select an existing one*
    - **Subscription**: *Your Azure subscription*
    - **Resource group**: *Create or select a resource group*
    - **Location**: *Select any available region*\*

    > \* Some Azure AI resources are constrained by regional model quotas. In the event of a quota limit being exceeded later in the exercise, there's a possibility you may need to create another resource in a different region.

1. Select **Create** and wait for your project to be created. This may take a few minutes.
1. When your project is created, you'll see the project home page.

## Create an agent

1. On the home page, select the **Build** tab, then on the **Agents** tab select **Create agent**.
1. Create your agent with a descriptive name, such as `product-expert-agent`.

When creating an agent, it will deploy the default model (like `gpt-4.1`). Once your agent is created, you'll see the agent playground with that default model automatically selected for you.

## Configure your data and Foundry IQ

Now you'll configure your agent that uses Foundry IQ to search the knowledge base.

1. First, give your agent the following instructions:

    ```
    You are a helpful AI assistant for Contoso, specializing in outdoor camping and hiking products. 
    You must ALWAYS search the knowledge base to answer questions about our products or product 
    catalog. Provide detailed, accurate information and always cite your sources.
    If you don't find relevant information in the knowledge base, say so clearly.
    ```

1. Select **Save** to save your current agent configuration.
1. Then, in the **Knowledge** section, expand the **Add** dropdown, and select **Connect to Foundry IQ**.
1. In the Foundry IQ setup window, select **Connect to an AI Search resource** and then **Create new resource** which should open up a dialog to create the resource.
1. Create a search resource with the default settings:
    - **Resource name**: *A globally unique name*
    - **Subscription**: *Your Azure subscription*
    - **Resource group**: *Use the same resource group as your project*
    - **Region**: *The same location as your project*
    - **Pricing tier**: Free *if available, otherwise choose Basic*
    - **Foundry IQ Knowledge base capabilities**: Pause til next month

Now you'll upload sample product information documents to connect to with Foundry IQ.

1. Locate the sample product files in the `assets/` folder of this lab:
   - `assets/contoso-backpacks-guide.pdf`
   - `assets/contoso-camping-accessories.pdf`
   - `assets/contoso-tents-catalog.pdf`

1. Open a new tab and navigate to the Azure portal at `https://portal.azure.com`. In the top search bar, search for **Storage accounts** and select **Storage accounts** from the services section.
1. Create a storage account with the following settings:
    - **Subscription**: *Your Azure subscription*
    - **Resource group**: *Use the same resource group as your project*
    - **Storage account name**: *A unique storage account name*
    - **Region**: *The same location as your project*
    - **Primary service**: *Azure Blob Storage or Azure Data Lake Storage*
    - **Performance**: *Standard*
    - **Redundancy**: *Locally-redundant storage (LRS)*
1. Once created, go to the storage account you created and select **Upload** from the top bar.
1. In the **Upload blob** blade, create a new container named `contosoproducts`.
1. Browse to the `assets/` folder, select all 3 PDF files, and select **Upload**.
1. Once your files are uploaded, navigate to the search service you created through the Foundry portal.
1. On the left pane, under **Security + networking** > **Keys**, select **Both** for API Access control and confirm the selection. Once complete, leave the Azure Portal tab open and navigate back to the Foundry portal tab and refresh the page.
1. Verify you are on the **Knowledge** page, select **Create a knowledge base**, choosing **Azure Blob Storage** as your knowledge source, then select **Connect**.
1. Configure your knowledge source with the following settings:
    - **Name**: `ks-contosoproducts`
    - **Description**: `Contoso product catalog items`
    - **Storage account name**: *Select your storage account*
    - **Container name**: `contosoproducts`
    - **Authentication type**: *API Key*
    - **Content extraction mode**: *minimal*
    - **Embedding model**: *Select the available deployed model, likely text-embedding-3-small*
    - **Chat completions model**: *Select the available deployed model, likely gpt-4.1*
1. Select **Create**.
1. On the knowledge base creation page, select the `gpt-4.1` model from the **Chat completions model** dropdown, leaving the rest of the field defaults as is.
1. Select **Save knowledge base**, and then refresh your browser to verify the knowledge source status is *active*. If it isn't yet, wait a minute and refresh your page until it is.
1. Select the back button to return to the **Knowledge** page, then select the **Manage** link next to the *Connection* drop-down.
1. Scroll down to the **Connected resources**, where you should see your search service. Select that row, find the **Authentication** section, and select **Edit authentication**.
1. Leaving the dialog open, return to the Azure portal tab which should still be on your search service **Keys** page. Copy one of those keys into the dialog in Foundry and select **Save**.

Your Foundry IQ settings should now be complete.

## Test the Agent in the playground

Before connecting from code, test your agent in the portal playground.

1. Navigate back to your agent on the **Build** > **Agents** page, and select the agent you created.
2. In the agent page, you should see a playground tab selected. Find the knowledge section and add Foundry IQ, selecting the connection and knowledge base you created.
1. Try the following test queries to verify the agent can retrieve information from the knowledge base:
    - `What types of tents does Contoso offer?`
    - `Tell me about which backpacks are available in XL.`
    - `What camping accessories are available?`

1. Review the responses and notice:
    - The agent provides specific information from the knowledge base
    - Citations or references to the source documents may be included
    - The agent stays focused on product information

1. You can also try interacting with your agent in the **Preview agent** for a more refined webapp experience.

1. In the agent details page, locate and copy the following information to a notepad (you'll need these later):
    - **Agent name**: This is the name you created (`product-expert-agent`)
    - **Project endpoint**: Found in the project settings or home page

### Configure the agent to require approval for tool calls

When you create an agent in the portal, its Foundry IQ (knowledge) tool runs **without** asking for approval by default. To ensure your app can review and control each knowledge base lookup, you'll change the agent to require approval before it uses tools with the Foundry Toolkit for VS Code extension.

> **Note**: The Foundry portal doesn't currently expose a setting to change this approval behavior, so you'll configure it from the Foundry Toolkit extension instead.

1. In Visual Studio Code, select **Extensions** from the left pane (or press **Ctrl+Shift+X**), then search the marketplace for the `Foundry Toolkit for VS Code` extension from Microsoft and select **Install** (if it isn't already installed).

    > **Note**: The extension is currently listed as **Foundry Toolkit**, but some VS Code labels, commands, or older screenshots may still refer to **AI Toolkit**. In this lab, treat those names as referring to the same extension experience.

1. Select the **Foundry Toolkit** icon in the sidebar, and sign in to your Azure account if you're prompted.
1. Under **Microsoft Foundry Resources**, choose **Set Default Project** and select the project you created earlier.
1. Expand the project section. Under **Prompt Agents**, select your `product-expert-agent` agent to open the **Agent Builder** window.
1. In the **Tools** section, find the **Foundry IQ** (knowledge base) tool and select its three dots (**...**) to open the tool configuration popup.

    > **Note**: The agent may list more than one tool. The Foundry portal adds a **Web search** tool to new agents by default, so be sure to select the three dots on the **Foundry IQ** knowledge base tool rather than another tool.
1. In the **Require approval before using tools** dropdown, select **Ask for approval for all tools**, and save your changes if you're prompted.

Your agent will now request approval each time it uses Foundry IQ to search the knowledge base, which the client app you complete next will handle.

## Connect to your agent from an app

Now you'll create a Python application to interact with your agent programmatically.

### Configure the application settings

1. In VS Code, open the **Python** folder in this lab directory.

1. In the **Python** folder, open the **.env** configuration file.
1. Replace the **your_project_endpoint** placeholder with the endpoint for your project (copied from the project **Home** page in the Foundry portal) and ensure that the AGENT_NAME variable is set to your agent name (which should be *product-expert-agent*).
1. After you've replaced the placeholder, save the file.

### Complete the agent client code

> **Tip**: As you add code, be sure to maintain the correct indentation. Use the comment indentation levels as a guide.

1. In VS Code, in the **Python** folder, open the **agent_client.py** code file.
1. Review the starter code that has been provided, including:
    - Import statements and configuration loading
    - The `send_message_to_agent()` function structure
    - The `display_conversation_history()` function
    - The main program loop

1. Find the first **TODO** comment and add the following code to connect to the project, get the OpenAI client, retrieve the agent, and create a new conversation:

    > **Tip**: Be careful to maintain the correct indentation level.

    ```python
    # Connect to the project and agent
    credential = DefaultAzureCredential(
        exclude_environment_credential=True,
        exclude_managed_identity_credential=True
    )
    project_client = AIProjectClient(
        credential=credential,
        endpoint=project_endpoint
    )

    # Get the OpenAI client
    openai_client = project_client.get_openai_client()

    # Get the agent
    agent = project_client.agents.get(agent_name=agent_name)
    print(f"Connected to agent: {agent.name} (id: {agent.id})\n")

    # Create a new conversation
    conversation = openai_client.conversations.create(items=[])
    print(f"Created conversation (id: {conversation.id})\n")
    ```

1. Find the second **TODO** comment inside the `send_message_to_agent()` function and add the following code to send messages and handle responses, including MCP approval requests:

    ```python
    # Add user message to the conversation
    openai_client.conversations.items.create(
        conversation_id=conversation.id,
        items=[{"type": "message", "role": "user", "content": user_message}],
    )
    
    # Store in conversation history (client-side)
    conversation_history.append({
        "role": "user",
        "content": user_message
    })
    
    # Create a response using the agent
    response = openai_client.responses.create(
        conversation=conversation.id,
        extra_body={"agent_reference": {"name": agent.name, "type": "agent_reference"}},
        input=""
    )

    # Check if the response output contains an MCP approval request
    approval_request = None
    if hasattr(response, 'output') and response.output:
        for item in response.output:
            if hasattr(item, 'type') and item.type == 'mcp_approval_request':
                approval_request = item
                break
    
    # Handle approval request if present
    if approval_request:
        print(f"[Approval required for: {approval_request.name}]\n")
        print(f"Server: {approval_request.server_label}")
        
        # Parse and display the arguments (optional, for transparency)
        import json
        try:
            args = json.loads(approval_request.arguments)
            print(f"Arguments: {json.dumps(args, indent=2)}\n")
        except:
            print(f"Arguments: {approval_request.arguments}\n")
        
        # Prompt user for approval
        approval_input = input("Approve this action? (yes/no): ").strip().lower()
        
        if approval_input in ['yes', 'y']:
            print("Approving action...\n")
            
            # Create approval response item
            approval_response = {
                "type": "mcp_approval_response",
                "approval_request_id": approval_request.id,
                "approve": True
            }
        else:
            print("Action denied.\n")
            
            # Create denial response item
            approval_response = {
                "type": "mcp_approval_response",
                "approval_request_id": approval_request.id,
                "approve": False
            }
        
        # Add the approval response to the conversation
        openai_client.conversations.items.create(
            conversation_id=conversation.id,
            items=[approval_response]
        )
        
        # Get the actual response after approval/denial
        response = openai_client.responses.create(
            conversation=conversation.id,
            extra_body={"agent_reference": {"name": agent.name, "type": "agent_reference"}},
            input=""
        )
    
    ```

1. After you've added the code, save the file.

## Test the Integration

Now you'll run your application and test the agent's ability to retrieve information from the knowledge base.

1. In VS Code, open an integrated terminal for the **Python** folder by right-clicking the folder and selecting **Open in Integrated Terminal**.
1. Create a virtual environment and install dependencies:

    ```
   python -m venv labenv
   ./labenv/Scripts/activate
   pip install -r requirements.txt
    ```

1. In the terminal pane, enter the following command to sign into Azure:

    ```
    az login
    ```

1. In the terminal pane, run your application:

    ```
   python agent_client.py
    ```

1. When the application starts, test the agent with the following queries:

    **Query 1 - Product Categories:**

    ```
    What types of outdoor products does Contoso offer?
    ```

    When prompted for approval, type **yes** to allow the agent to search the knowledge base.

    **Query 2 - Specific Product Details:**

    ```
    Tell me about the weatherproof features of your tents.
    ```

    **Query 3 - Product Comparisons:**

    ```
    What's the difference between your daypacks and expedition backpacks?
    ```

    **Query 4 - Accessories and Add-ons:**

    ```
    What camping accessories would you recommend for a weekend hiking trip?
    ```

    **Query 5 - Follow-up Question:**

    ```
    How much do those items typically cost?
    ```

    Notice how the agent maintains conversation context from your previous query.

1. Type `history` to view the complete conversation history.

1. Type `quit` when you're done testing.

## Clean up

If you've finished exploring Azure AI Agent Service and Foundry IQ, you should delete the resources you have created in this exercise to avoid incurring unnecessary Azure costs.

1. In a web browser, open the [Azure portal](https://portal.azure.com) at `https://portal.azure.com`.
1. Navigate to the resource group containing your Foundry resource and AI Search resources.
1. On the toolbar, select **Delete resource group**.
1. Enter the resource group name and confirm that you want to delete it.
