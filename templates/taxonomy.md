# {Experience name} conversation taxonomy

Classify each conversation or tool-log session into one record.

- **intent**: what the user wanted, five words or fewer. Examples: {three intent examples from your brief}.
- **tier**: {your severity levels, or delete this field}
- **outcome**: `resolved`, `partial`, `failed` (nothing useful and no handoff), `escalated` (handed to a human).
- **tools_used**: tool names that appear.
- **unmet_need**: true when the user asked for something no available tool could do, even if the assistant declined gracefully. A polite "I can't do that yet" is still an unmet need.
- **unmet_need_description**: one sentence.
- **proposed_tool**: snake_case, reused across conversations for the same need: {tool names you expect; reuse them}. Empty when none.
- **evidence_quote**: the single user line that best shows the need, verbatim.

Rules: a request that was properly handed off is `escalated` and not an unmet need. A request the agent could not perform is an unmet need with a proposed tool even when the agent passed it to a human. Never propose a tool that would give advice outside the agent's mandate; if a user wanted that, set unmet_need true and proposed_tool empty so the count shows the demand without a tool.
