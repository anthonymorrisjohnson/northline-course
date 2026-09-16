# Front doors

This page is for deciding, for one AI experience, whether you hand the customer tools or you run the conversation yourself.

Northline Care built one set of tools and put them behind two doors. Patients talk to a page Northline wrote. Prairie Health Plan's analyst talks to the same data from her own Claude Code. The tools are the cheap part. The door is the strategy, because the door decides who owns the loop, what you get to see, and who is answerable when it goes wrong.

## The two doors, side by side

| Dimension | MCP given to the customer | Controlled agent you host |
|---|---|---|
| Who runs the loop | Their agent, their prompt, their model | You |
| Distribution | Wherever they already work | They have to come to you |
| What you see | Tool calls: name, arguments, status | Every word, including what you could not do |
| Guardrails | You can refuse inside a tool; you cannot shape what is said around it | Yours, end to end |
| Who pays for tokens | They do | You do |
| Liability when it misspeaks | Shared and unclear | Yours, and clear |
| Build cost | The tool layer only | Tool layer plus prompt, UI, hosting, logging |
| Time to first user | Days if they already have an agent | Weeks |
| What Prairie saw | 78% engagement, tenfold readings | Nothing; they never asked for escalations |

## Row by row, with Northline

**Who runs the loop.** Prairie's analyst wrote her own prompt, in her own session, on her own schedule. Northline never saw it and cannot change it. On the patient side the prompt is a file Northline owns, `northline/agent/brief.md`, and changing one line changes what every patient is told that week.

**Distribution.** Prairie's analyst already had Claude Code open. Adding Northline meant adding one server to her config, and she was pulling evidence the same day. A patient cannot be reached that way. Northline had to build a page, run it, and text people a link, and nine months later 78% of them answer weekly.

**What you see.** From Prairie, Northline sees lines like `enrollment_status({"member_id": "Sandra Okonkwo"}) -> not_found`. Name, arguments, status. From a patient, Northline sees the sentence: "I've been out of lisinopril for three days. My truck's been in the shop and the pharmacy is 45 miles away." One of those is a feature request. The other is a person.

**Guardrails.** Inside a tool you can refuse. `enrollment_status` returns `not_found` for a name it cannot match, and that is the whole of Northline's control over what Prairie's agent does next. On the patient page, Northline controls the sentence around the refusal: the check-in agent has to say plainly that it cannot help with insurance, say what it can do, and offer to note it for a human.

**Who pays for tokens.** Prairie's analyst pays for Prairie's analyst. Every patient turn is on Northline's bill, every week, for 40,000 people.

**Liability when it misspeaks.** When the check-in agent told a patient "median response time right now is 31 hours", that was Northline speaking, in writing, to a patient. If Prairie's agent reads `outcome_evidence` and tells a Prairie executive something wrong, whose sentence that was is a matter for the lawyers.

**Build cost.** The plan door is four functions in `northline/tools/plan.py` and an entry in `.mcp.json`. The patient door is those four plus a written brief, a web page, a server, a transcript store, and someone who reads the transcripts.

**Time to first user.** Days for the customer who already has an agent. Weeks for the one who does not, because a controlled agent is a product and a product needs a brief, a page, hosting and logging before the first person can use it.

**What Prairie saw.** Engagement at 78% a week and readings up from 12,000 a month to 120,000. Those numbers are why the contract is on the table. Across the forty committed Prairie sessions there is not one call about escalations or nurse response time, because Northline never built a tool that answers that question. The customer saw the outcomes. Nobody showed them the queue.

## The hybrid

You do not have to choose once. Build the tool layer once. Consume it from your own agent for the persona who needs a product. Publish the same server to the customer who already has an agent.

That is what this repo is. `northline/tools/` holds the functions. The registry decides which persona sees which tool. The check-in agent and the MCP server are two thin things sitting on the same set of functions, and a tool added for one door is available at the other the moment it is registered.

## Where each front door sits at Northline

**Patients get the controlled agent.** The channel is SMS, so there is no app to plug into and nowhere else for them to be. More than that: every word is signal. The refill requests, the 45-mile drive to the pharmacy, the cuff that shows ERR, the person who has not seen anybody since the snow started — none of that arrives as a tool call. It arrives as a sentence, and only because Northline owns the loop does it get logged at all.

**Health plans get MCP.** Prairie already has an analyst with an agent. They need the tools, not a product, and building them a portal would have delayed the deal by months. Tool calls were signal enough: 39 of the 187 calls in the committed sessions came back `not_found`, almost all of them `enrollment_status` called with a person's name instead of a member id. That is a clear product requirement, and nobody had to write a word for Northline to read it.
