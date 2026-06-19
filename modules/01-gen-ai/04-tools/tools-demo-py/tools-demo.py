import os
import json
from datetime import datetime
from dotenv import load_dotenv
from azure.identity import DefaultAzureCredential
from azure.ai.projects import AIProjectClient


# ---------- Simulated tool implementations ----------

def get_current_weather(location: str, unit: str = "celsius") -> dict:
    """Simulated weather lookup — returns fake but plausible data."""
    mock_data = {
        "london":    {"temperature": 14, "condition": "Cloudy", "humidity": 78},
        "paris":     {"temperature": 18, "condition": "Partly Sunny", "humidity": 60},
        "new york":  {"temperature": 22, "condition": "Sunny", "humidity": 55},
        "tokyo":     {"temperature": 26, "condition": "Humid", "humidity": 85},
    }
    key = location.lower()
    weather = mock_data.get(key, {"temperature": 20, "condition": "Unknown", "humidity": 65})
    if unit == "fahrenheit":
        weather["temperature"] = round(weather["temperature"] * 9 / 5 + 32)
    weather["unit"] = unit
    weather["location"] = location
    return weather


def get_business_hours(business_name: str) -> dict:
    """Simulated business hours lookup."""
    mock_hours = {
        "coffee shop":   {"weekday": "07:00–20:00", "weekend": "08:00–18:00", "open_now": True},
        "pharmacy":      {"weekday": "08:00–22:00", "weekend": "09:00–17:00", "open_now": True},
        "supermarket":   {"weekday": "06:00–23:00", "weekend": "07:00–22:00", "open_now": True},
        "post office":   {"weekday": "09:00–17:00", "weekend": "Closed", "open_now": False},
    }
    key = business_name.lower()
    return mock_hours.get(key, {"weekday": "09:00–18:00", "weekend": "Closed", "open_now": None})


# ---------- Tool definitions sent to the model ----------

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "get_current_weather",
            "description": "Get the current weather for a specified city.",
            "parameters": {
                "type": "object",
                "properties": {
                    "location": {
                        "type": "string",
                        "description": "The city name, e.g. 'London' or 'Tokyo'",
                    },
                    "unit": {
                        "type": "string",
                        "enum": ["celsius", "fahrenheit"],
                        "description": "Temperature unit. Defaults to celsius.",
                    },
                },
                "required": ["location"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_business_hours",
            "description": "Look up the opening hours of a local business.",
            "parameters": {
                "type": "object",
                "properties": {
                    "business_name": {
                        "type": "string",
                        "description": "Type of business, e.g. 'coffee shop' or 'pharmacy'",
                    },
                },
                "required": ["business_name"],
            },
        },
    },
]


# ---------- Tool dispatcher ----------

def dispatch_tool(name: str, arguments: dict) -> str:
    if name == "get_current_weather":
        result = get_current_weather(**arguments)
    elif name == "get_business_hours":
        result = get_business_hours(**arguments)
    else:
        result = {"error": f"Unknown tool: {name}"}
    return json.dumps(result)


# ---------- Agentic loop ----------

def run_agent(openai_client, model_deployment: str, user_message: str) -> str:
    messages = [
        {
            "role": "system",
            "content": (
                "You are a helpful local information assistant. "
                "Use the available tools to answer questions about weather and businesses. "
                f"Today is {datetime.now().strftime('%A, %d %B %Y')}."
            ),
        },
        {"role": "user", "content": user_message},
    ]

    # Agentic loop: keep calling the model until it stops requesting tools
    while True:
        response = openai_client.chat.completions.create(
            model=model_deployment,
            messages=messages,
            tools=TOOLS,
            tool_choice="auto",
        )

        choice = response.choices[0]

        if choice.finish_reason == "tool_calls":
            assistant_message = choice.message
            messages.append({"role": "assistant", "content": assistant_message.content, "tool_calls": [
                {
                    "id": tc.id,
                    "type": "function",
                    "function": {"name": tc.function.name, "arguments": tc.function.arguments},
                }
                for tc in assistant_message.tool_calls
            ]})

            for tool_call in assistant_message.tool_calls:
                fn_name = tool_call.function.name
                fn_args = json.loads(tool_call.function.arguments)
                print(f"  [tool call] {fn_name}({fn_args})")
                tool_result = dispatch_tool(fn_name, fn_args)
                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": tool_result,
                })

        else:
            return choice.message.content.strip()


def main():
    os.system('cls' if os.name == 'nt' else 'clear')

    try:
        load_dotenv()
        project_endpoint = os.getenv("PROJECT_CONNECTION")
        model_deployment = os.getenv("MODEL_DEPLOYMENT")

        project_client = AIProjectClient(
            credential=DefaultAzureCredential(
                exclude_environment_credential=True,
                exclude_managed_identity_credential=True
            ),
            endpoint=project_endpoint,
        )

        openai_client = project_client.get_openai_client(api_version="2024-10-21")

        print("Local Information Agent — Tool Use Demo")
        print("=" * 45)
        print("This agent can look up weather and business hours.")
        print("Example questions:")
        print("  - What's the weather like in Paris?")
        print("  - Is the pharmacy open right now?")
        print("  - What's the weather in Tokyo in Fahrenheit, and are any coffee shops open?")
        print("\nType 'quit' to exit.\n")

        while True:
            user_input = input("You: ").strip()
            if user_input.lower() == "quit":
                print("Goodbye!")
                break
            if not user_input:
                continue

            print("Agent thinking...\n")
            answer = run_agent(openai_client, model_deployment, user_input)
            print(f"\nAgent: {answer}\n")

    except Exception as ex:
        print(f"\nError: {ex}")


if __name__ == '__main__':
    main()
