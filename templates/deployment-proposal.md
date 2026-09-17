# Deployment proposal: `{agent_name}`

**Kind:** agent  **Placement:** {placement}

## Why
{purpose}

Evidence from the queue log: {escalations_per_week} escalations a week, median nurse response {median_h} hours (p90 {p90_h}), {non_clinical_pct}% of the nurse queue is non-clinical, {unanswered} escalations unanswered over 24 hours from {inactive} patients.

## Tools it needs
{tools_needed}

## Decisions a human must make before it goes live
{decisions}

## Acceptance test
{acceptance_test}

## Metrics it should move
{metrics}

## Risks
{risks}

## Decision
- [ ] Approve: `/northline-deploy {agent_name}`
- [ ] Reject, reason:
