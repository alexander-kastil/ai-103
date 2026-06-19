# Agent Framework Evaluation & Prompt Optimization

## When to Use

- Setting up evaluation datasets from agent traces
- Running batch evaluations
- Comparing evaluation runs to measure prompt improvements
- Optimizing agent prompts
- Tracking quality metrics over time

## Evaluation Flow

```
Agent traces → Dataset curation → Eval run → Results → Prompt iteration
```

1. **Collect traces**: Run the agent on sample inputs, capture input/output pairs
2. **Curate dataset**: Select representative examples, add expected outputs
3. **Run eval**: Batch-evaluate the agent against the dataset
4. **Compare**: Diff results against previous runs
5. **Optimize**: Iterate on prompts based on eval findings

## Foundry Eval Tooling

Use the `microsoft-foundry` skill for:

- Creating eval datasets from traces: curate input/output pairs from agent runs
- Running batch eval: evaluate agent against dataset with scoring rubric
- Comparing runs: diff two eval runs to measure improvement
- Prompt optimization: automated prompt iteration based on eval results

## Example: `<agent-project>`

| Agent | Key metrics |
| --- | --- |
| Writer | Voice adherence, structure, SEO quality |
| Reviewer | Verdict accuracy, feedback specificity |
| Translator | Terminology accuracy, register consistency |
| Researcher | Source relevance, brief completeness |
| Publisher | Format compliance, manifest validity |
