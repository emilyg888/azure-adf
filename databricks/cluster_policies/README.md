# Databricks Cluster Policies

## All-Purpose Auto-Termination Policy

`all_purpose_autotermination_20m.json` constrains future all-purpose clusters to auto-terminate after 15 to 30 minutes of inactivity, defaulting to 20 minutes.

Create the policy:

```bash
databricks cluster-policies create \
  --name "All-Purpose Auto-Termination 20m" \
  --description "Requires all-purpose clusters to auto-terminate after 15-30 minutes of inactivity. Default is 20 minutes." \
  --definition "$(cat databricks/cluster_policies/all_purpose_autotermination_20m.json)" \
  --profile fleet-dev-active
```

List policies:

```bash
databricks cluster-policies list --profile fleet-dev-active
```

If the policy already exists, get its policy ID from the list output and update it:

```bash
databricks cluster-policies edit <policy-id> \
  --name "All-Purpose Auto-Termination 20m" \
  --description "Requires all-purpose clusters to auto-terminate after 15-30 minutes of inactivity. Default is 20 minutes." \
  --definition "$(cat databricks/cluster_policies/all_purpose_autotermination_20m.json)" \
  --profile fleet-dev-active
```

