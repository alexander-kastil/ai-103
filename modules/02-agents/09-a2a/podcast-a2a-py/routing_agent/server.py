import os
import asyncio
from fastapi import FastAPI, Request
from dotenv import load_dotenv
from contextlib import asynccontextmanager
from routing_agent.agent import RoutingAgent

load_dotenv()

routing_agent = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    global routing_agent
    print("Starting up: Initializing routing agent...")
    server_url = os.environ["SERVER_URL"]
    title_port = os.environ["TITLE_AGENT_PORT"]
    segment_port = os.environ["SEGMENT_AGENT_PORT"]
    routing_agent = await RoutingAgent.create([
        f"http://{server_url}:{title_port}",
        f"http://{server_url}:{segment_port}",
    ])
    routing_agent.create_agent()
    print("Routing agent initialized.")
    yield

app = FastAPI(lifespan=lifespan)

@app.post("/message")
async def handle_message(request: Request):
    print("Agent: Processing request, please wait.")

    data = await request.json()
    user_message = data.get("message")

    if not user_message:
        return {"error": "No message provided."}

    try:
        response = await routing_agent.process_user_message(user_message)

    except Exception as e:
        return {"error": f"Failed to process message: {str(e)}"}

    return {"response": response}

@app.get("/health")
async def health_check():
    return {"status": "Routing agent is running!"}

if __name__ == "__main__":
    import uvicorn
    host = os.environ["SERVER_URL"]
    port = int(os.environ["ROUTING_AGENT_PORT"])
    uvicorn.run("routing_agent.server:app", host=host, port=port, reload=True)
