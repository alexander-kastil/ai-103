# Work IQ Tenant Setup

One-time provisioning required before Part 4 of the 05-m365 demo. Each step must complete in order — later steps silently fail or return confusing errors if an earlier step is missing.

**Who can do what:**

| Step | Required role |
|---|---|
| 1. Provision the service principal | Global Administrator |
| 2. Accept the EULA | Any user |
| 3. Grant consent | Any user (after SP exists) |
| 4. Activate billing | Global Admin or Billing Admin |
| 5. Run a query | Any user in the billing policy scope |

---

## Step 1 — Provision the Work IQ service principal (one-time, Global Admin)

This is the root cause of `Your tenant does not yet have the WorkIQ service configured` and the WAM `IncorrectConfiguration` error on `workiq auth consent`. Must be done before any other step.

**Option A — Azure CLI:**

```azurecli
az ad sp create --id fdcc1f02-fc51-4226-8753-f668596af7f7
```

**Option B — Graph Explorer** (if you prefer a browser):

1. Go to [Graph Explorer](https://developer.microsoft.com/graph/graph-explorer) and sign in with a Global Admin account.
2. Set method to **POST** and URL to `https://graph.microsoft.com/v1.0/servicePrincipals`.
3. Select **Modify permissions**, consent to `Application.ReadWrite.All`.
4. Enter the request body and run the query:

```json
{
  "appId": "fdcc1f02-fc51-4226-8753-f668596af7f7"
}
```

`201 Created` = success. A conflict response means the SP already exists — continue.

The SP exposes scope `WorkIQAgent.Ask` (scope ID `0b1715fd-f4bf-4c63-b16d-5be31f9847c2`), audience `api://workiq.svc.cloud.microsoft`.

---

## Step 2 — Accept the EULA

```bash
workiq accept-eula
```

---

## Step 3 — Grant admin consent

```bash
workiq auth consent
```

This is an interactive sign-in. It only works after Step 1 completes. The CLI authenticates against the signed-in account's home tenant — use `workiq config` and `workiq auth login` to manage the account if needed.

---

## Step 4 — Activate usage-based billing (portal only, Global Admin or Billing Admin)

This is a **portal-only step** — it cannot be scripted. A plain `403 Forbidden` on `workiq ask` (no scope error in the response) means this step is missing.

Work IQ API reached GA on 2026-06-16 with consumption-based pricing via Copilot Credits. No usage is possible until a billing policy is active.

1. Go to the [Microsoft 365 admin center](https://admin.microsoft.com).
2. Navigate to **Copilot** > **Cost Management** > **Get Started**.
3. Activate a spending policy: select an Azure subscription, set monthly or per-user limits and alerts, and save.
4. Ensure the user running the demo is in scope of the policy (e.g., an "All users" policy covering Work IQ API).
5. **Wait 15–30 minutes** before retrying — the index takes time to build after billing is activated.

---

## Step 5 — Run a query

```bash
workiq ask -q "summarize my recent store-ops emails"
```

Add `-v` for request-ID and conversation-ID diagnostics.

---

## Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| `Your tenant does not yet have the WorkIQ service configured` | Work IQ SP not provisioned | Complete Step 1, then retry Step 3 |
| WAM `IncorrectConfiguration` (error 3399614468 / 3399614466) on `workiq auth consent` | SP not provisioned (3399614468), or a custom app registration missing broker redirect URI `ms-appx-web://microsoft.aad.brokerplugin/<client_id>` (3399614466) | Complete Step 1; for custom app registrations add the broker redirect URI |
| `403 Forbidden` (no scope error) | User not covered by a usage-based billing plan | Complete Step 4, wait 15–30 min, retry |
| `403 Forbidden` with `Required scopes = [...]` | Admin consent for `WorkIQAgent.Ask` not granted | Rerun `workiq auth consent` (Step 3) |
| `401 Unauthorized` | Token audience mismatch — token must be issued for `api://workiq.svc.cloud.microsoft` | Check the token audience claim |
| Empty response / no agent text | Billing or license assigned recently — index still building | Wait 15–30 minutes and retry |

---

## References

- [Enable your tenant for Work IQ](https://learn.microsoft.com/microsoft-365/copilot/extensibility/work-iq/enable-work-iq)
- [Microsoft Work IQ CLI](https://learn.microsoft.com/microsoft-365/copilot/extensibility/work-iq/cli)
- [Understand usage-based billing and Copilot Credits](https://learn.microsoft.com/microsoft-365/copilot/usage-based-billing-overview-copilot-credits)
