import os
from azure.identity import DefaultAzureCredential
from azure.ai.projects import AIProjectClient

endpoint = "https://ai-103-demos-resource.services.ai.azure.com/api/projects/ai-103-demos"
cred = DefaultAzureCredential(
    exclude_environment_credential=True,
    exclude_managed_identity_credential=True,
)
pc = AIProjectClient(endpoint=endpoint, credential=cred)

print("=== agents attr methods ===")
print([m for m in dir(pc.agents) if not m.startswith("_")])

names = []
try:
    for a in pc.agents.list_versions():
        names.append(getattr(a, "name", str(a)))
except Exception as e:
    print("list_versions failed:", type(e).__name__, e)

if not names:
    try:
        for a in pc.agents.list():
            names.append(getattr(a, "name", str(a)))
    except Exception as e:
        print("list failed:", type(e).__name__, e)

print("=== agent/workflow names ===")
for n in sorted(set(names)):
    print(" -", n)

target = "Contoso-Job-Application-Triage"
print(f"=== target '{target}' present: {target in names} ===")
