# Agent Framework API Bridge — .NET ↔ Python Contract Bridge

## When to Use

- Adding a new API endpoint that calls a hosted agent
- Changing the JSON output format of an agent and updating the .NET deserialization
- Adding a new `FoundryAgents` config entry for a new agent
- Ensuring request DTOs, response DTOs, and agent JSON output stay in sync

## The Bridge Pattern

Every hosted agent operation follows this flow:

```
.NET Controller → .NET Service → AIProjectClient → Hosted Agent (Python) → JSON response → .NET Service deserializes
```

The JSON contract is the bridge. Both sides must agree on field names and types.

## Adding a New Endpoint

1. **Define the contract** — agree on request and response shapes
2. **Update the agent** — ensure it returns the agreed JSON format
3. **Create the .NET DTO** — matching C# record/class
4. **Add the controller action** — with route, auth, and input validation
5. **Wire the service** — call the hosted agent, deserialize response
6. **Add config** — `FoundryAgents` entry in `appsettings.json`

## Example: `<agent-project>`

```json
// Request (from .NET to agent)
{ "operation": "create-article", "keyword": "...", "pillar": "...", "audience": "..." }

// Response (from agent to .NET)
{ "article": "...", "seoMeta": {...}, "socialPosts": {...}, "usage": {...} }
```

See `src/<api-project>/Controllers/<Domain>Controller.cs` and `src/<api-project>/Services/<Domain>Service.cs`.
