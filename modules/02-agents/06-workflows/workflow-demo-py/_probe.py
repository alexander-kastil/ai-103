import os
from dotenv import load_dotenv
from azure.identity import DefaultAzureCredential
from azure.ai.projects import AIProjectClient

load_dotenv()
endpoint = os.environ["PROJECT_ENDPOINT"]
print("ENDPOINT:", endpoint)
with DefaultAzureCredential(exclude_environment_credential=True, exclude_managed_identity_credential=True) as cred, \
     AIProjectClient(endpoint=endpoint, credential=cred) as pc, \
     pc.get_openai_client() as oai:
    print("=== assistants.list ===")
    try:
        names=[]
        for a in oai.beta.assistants.list(limit=100):
            names.append((getattr(a,'name',None), getattr(a,'id',None)))
        for n in names: print("ASSISTANT:", n)
        print("COUNT:", len(names))
    except Exception as e:
        print("assistants.list error:", repr(e))
