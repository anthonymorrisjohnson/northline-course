# Session plan, 75 minutes

This page is for the two people running the session: what happens minute by minute, what to type, what to have open, and what to do when something breaks.

Two front doors appear on screen: the check-in page Northline hosts, and MCP (Model Context Protocol, the standard way to hand an assistant a set of tools), which is how Prairie's own analyst reaches the same data.

The paper case runs first and runs whole. The laptops come out at minute 25. Attendees type two commands all session: `/pm-run` and `/deploy triage`.

## Pre-work, three days ahead

Send this to every attendee three days before the session. It takes about ten minutes and it has to happen before the day, not on it.

1. Install the Claude desktop app and sign in. Claude Code is the Code tab inside it.
2. In Claude Code, click New project, create a new empty folder, and name it `northline`.
3. Paste: `Download github.com/anthonymorrisjohnson/northline-course as a ZIP, unzip it so the files sit directly in this folder, then delete the zip.`
4. When it is done, close the project and open it again.
5. Type `/northline-setup` and follow the prompts.
6. Paste the `READY: ...` line it prints into the workshop group chat.

Nothing else to install. `/northline-setup` handles the rest, on macOS, Linux and Windows. The desktop app works the same on Mac and Windows. Anyone who prefers a terminal can unzip the folder, `cd` into it and run `claude`; on Windows that route needs the native Claude Code installer, not npm, because the npm `claude.cmd` shim cannot take the long prompts the classification step sends.

Every laptop makes 40 to 70 model calls during the session on its own Claude subscription. Warn attendees on the Pro plan that a re-test in `/deploy` costs another 15 calls, and expect one or two laptops to hit a limit in the room.

Watch the group chat as the READY lines arrive. Every line names an operating system and a count of tools; a line that does not appear is a person to help before the day. If someone cannot get there, they follow on paper — every output the session produces is already committed in the folder.

## Two roles

**Room.** Runs the paper: reads the Monday email, hands out role cards, keeps time, asks the seven questions, calls on people, chairs the board meeting. Never touches a keyboard.

**Screen.** Drives the one machine that is projected: the dashboard, the check-in page, and the two commands. Types what the room decides, out loud, slowly enough to be followed. Never explains while typing.

The split matters. A single person doing both will fill the classification wait with typing instead of talking, and the wait is where half the teaching happens.

## Run of show

| Minutes | Room | Screen | Slides | Presenter notes |
|---|---|---|---|---|
| 0–3 | Monday email aloud, role cards out | Dashboard, "Northline ops, last quarter" | 1 setup (up as people arrive), 2 title, 3 the email, 4 roles and the question | Open `http://127.0.0.1:8765/dashboard`. Do not explain the table. Land: "Everything on this screen is true, and the board is about to sign a contract on it." |
| 3–15 | Read exhibits in role; pocket memo at minute 12 | At minute 8, a three-minute Prairie demo: her own agent pulls outcome evidence over MCP | 4 stays up, then the dashboard; 5 two front doors, after the Prairie demo | Have a Claude Code session open in the folder. Ask it for Prairie's engagement and outcome evidence, in your own words. Land: "That is the customer's agent, not ours. We built the tools; they run the loop." |
| 15–25 | Board recommendation on paper, in teams | Idle, dashboard still up | none; the dashboard | No laptops. Keep it to ten minutes even if nobody is finished. Land: "Hold on to your recommendation. You are going to check it against the logs." |
| 25–42 | Do-along; the seven questions | `/pm-run`, then `/deploy triage` | 6 the loop, 7 board deck vs logs, 8 the gate question, 9 the proposals, 10 four decisions, 11 what did it do with 184/112 | See the block below. |
| 42–50 | Board meeting, two teams, pushback | A team's projection on the dashboard | 12 pushback questions, one per click | Toggle **Sign Prairie** on the team's own numbers while they present. Land: "Your recommendation is now a line on a chart. Defend it." |
| 50–62 | Debrief themes; "where is this hiding in your market?" | Before, after the agent, after triage, side by side | 13 what just happened, one line per click; 14 who runs the loop; 15 your market | Have `docs/04-operating.md` open for the fee argument. Land: "The agent worked. The operating model around it did not, and that was a decision, not a fact about the technology." |
| 62–75 | Case one closer, or buffer | Off | 16 take it home | Buffer first. If minute 42 slipped, this is where you took the time from. |

Slide numbers are for the browser deck at `/slides` and its PowerPoint export, `slides/present.pptx`. After editing `slides/present.html`, rebuild the export with `uv run --with python-pptx python scripts/export_deck.py`. `slides/deck.pptx` is the earlier editable PowerPoint deck and has its own numbering.

## What the room sees

Slides carry the framing and the questions. The live system carries the evidence. When a slide and the live system would show the same thing, show the live system.

- **Slides:** arrival, the email, the roles and the question, every question you ask the room, and the debrief.
- **The dashboard:** while teams read and write their recommendation, after the triage deploys, and during the board meeting.
- **Claude Code:** only when something is being typed or has just printed: the Prairie demo, `/pm-run`, the diagnosis, `/deploy triage`, and the acceptance table.
- **Never on the projector:** the presenter window, the nurse's key, and `docs/`.

## The do-along, minute by minute

**First, the server.** Say it once, slowly, and put it on the screen. In Claude Code, everyone pastes: `Start the check-in server in the background with uv run python -m northline.agent.server and tell me when http://127.0.0.1:8765 answers.` (Terminal users: a second window, `cd` into the folder, run that command, leave the window alone.) Then everyone opens `http://127.0.0.1:8765` and texts the agent one reading, "my BP was 184/112", so their own conversation is in the logs before the loop runs. Two minutes, no more; anyone who is not there watches the screen.

**Type `/pm-run`.** It says how many items it is about to classify, then runs. The whole thing takes about five minutes: roughly two and a half in classification, half a minute for the diagnosis, a minute and a half for the proposals.

Talk through the classification wait. It is the only long pause in the session and it is the best two and a half minutes you have: explain what is being read, what a record looks like, and that the counting afterwards is plain Python. Do not fill it with typing.

**When the report appears**, put the two-column table on the screen and read the left column first. The board was not wrong. Then read the two rows where the logs have a number and the deck says "not reported".

**Ask question 1** — the gate — and take three answers from the room before revealing the diagnosis.

**Pick triage.** If the room picks a tool, the loop pushes back once with the metric that choice moves, and then accepts whatever they say. Let it.

**Type `/deploy triage`.** Four decisions, one at a time, voted by the room. Fill slide 6 live as each one lands. With all four defaults the acceptance table comes back clean and there is no miss to read, so the lesson lives in Decision 1: if the room is drifting toward the default thresholds, ask "Is 180/110 too cautious? Northline's nurses are already drowning." A vote for 190/115 produces the 184/112 miss the rest of the session is built on.

**When the acceptance table prints**, stop. Read the misses before anything else. Quote the message and the nurse's note for every trap that failed. Then ask question 7.

**Only then** switch to the dashboard. The urgent-cases-missed tile first, the nurse response line second, the Sign Prairie toggle last — without, then with.

**Close with the board chair's question:** "What did your triage do with 184/112?"

## The seven questions, in order

1. In one sentence, what is the problem the board doesn't see? *(asked before the diagnosis is shown; take three answers)*
2. Which proposal do you want to pursue, and why?
3. What are your urgent thresholds — blood pressure, glucose, and the words that are always urgent?
4. Non-clinical messages: admin, an auto-reply from approved content, or hold for the morning?
5. An urgent message at 1:48am: tell them to call 911 and page the on-call nurse, tell them to call 911 only, or queue it for the morning?
6. A patient says "don't tell the doctor". Do you honour it?
7. Do you deploy it as is, or change a decision and re-test?

Questions 3 to 6 each come with the Northline default. Say it is what Northline's product team chose, and say that taking it is a decision that gets recorded as one. Do not let the room take all four defaults without a vote.

## Fallbacks

**The wifi dies.** Almost everything here is local: the tools, the server, the dashboard, the simulator, the corpus, the reports. Only the model calls need the network, which means `/pm-run` and the acceptance run are the two things that stop. Every output they produce is already committed, so switch to a read-through: open `northline/pm/out/report.md`, then `diagnosis.md`, then `proposals/agent-triage.md`, and ask the seven questions exactly as written. You lose the live numbers. You keep the whole lesson.

**A laptop falls behind.** Tell them to stop typing and watch the screen. The file names are on the slide and every file is in their folder; they can re-run anything afterwards. Nobody debugs a laptop during the do-along, including you.

**A laptop says "Prompt is too long".** This happens when someone has a lot of other tools connected to their own Claude Code. It affects their chat window, not this folder: every script here runs with only Northline's tools loaded, so `/pm-run` and `/deploy triage` still work. Tell them to start a fresh session in the folder and carry on.

**The acceptance run fails.** Re-run it once — `uv run python -m northline.agents.triage.acceptance`. If it fails again, do not debug it in front of the room. Open `docs/03-triage-decisions.md` and use the nurse's key table instead: walk messages 5, 9, 12 and 13, ask the room what their thresholds would have done with each, and go to the dashboard from there. The lesson is the miss, not the script that found it.

## What to have open before you start

- The deck, `http://127.0.0.1:8765/slides`, on the projector. Press P for the presenter window (notes, timer, next slide) and keep that one on your laptop; F for full screen. Arrow keys in either window move both.
- The dashboard, `http://127.0.0.1:8765/dashboard`, in the next tab, with the check-in server running.
- A Claude Code session in the course folder, for Prairie's demo at minute 8 and for the two commands.
- `docs/03-triage-decisions.md`, for the nurse's key.
- `docs/04-operating.md`, for the fee argument in the debrief.
