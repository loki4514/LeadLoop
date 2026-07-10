# LeadLoop — Product FAQ Knowledge Base

A RAG-ready reference describing how the LeadLoop AI Lead Qualification &
Follow-up Agent works. Each entry is self-contained so it can be retrieved and
answered on its own.

---

## What is LeadLoop?

LeadLoop is an AI-powered lead qualification and follow-up agent for real estate
teams. It captures inbound leads from a web chat widget (with Telegram planned),
qualifies them through a guided conversation, matches them to available properties,
captures their contact details, scores them Hot/Warm/Cold, and auto-assigns them to
an employee. It also runs a background job that drafts follow-up emails for idle
leads and notifies the assigned employee to approve and send them.

## What channels does LeadLoop support for capturing leads?

At launch, LeadLoop captures leads through an **embedded web chat widget** on the
company website. Each conversation is tied to a lead record and stored with a
channel label (currently `web`). **Telegram** support is planned as a second channel,
reusing the same qualification and scoring logic, so leads from either channel flow
into the same pipeline and dashboard.

## What questions does the qualification agent ask?

The agent asks the minimum set of questions needed to score a lead without causing
drop-off:

1. **Location** — the area or city the buyer is looking in.
2. **BHK / configuration** — 1/2/3 BHK, villa, etc.
3. **Budget range** — the heaviest qualifying signal.
4. **Timeline** — when they intend to buy or move (urgency).
5. **Purpose** — own use, investment, or just exploring (intent).
6. **Financing** — loan needed, ready cash, or unsure (readiness).

After collecting location, BHK, and budget, the agent shows matching properties
before asking the remaining questions and then requesting contact details.

## In what order does the agent ask questions, and why?

The order is deliberate to maximize conversion:

1. Ask **location → BHK → budget** first — enough to search inventory.
2. **Show 3 matching properties** to deliver value before asking for anything personal.
3. Ask **timeline → purpose → financing** to deepen qualification.
4. Finally, ask for a **callback with email and phone** — the conversion ask comes
   *after* value is delivered, not before.

Asking for contact details up front increases drop-off; showing relevant properties
first builds trust and makes the lead more willing to share contact information.

## How does LeadLoop match properties to a lead?

Once the agent has the lead's location, BHK, and budget, it queries the property
inventory for listings that match those constraints. Properties are stored with
title, location, BHK, price, area, and description, and are indexed on
location + BHK + price for fast filtering. The agent typically returns the top three
matches to show the lead during the conversation.

## How does lead scoring work (Hot / Warm / Cold)?

Each qualified lead receives a numeric score that maps to a tier:

- **Budget** carries the heaviest weight — it best separates serious buyers from
  browsers.
- **Timeline** carries heavy weight — a near-term buyer is hotter than someone
  looking a year out.
- **Purpose** carries moderate weight — own-use and investment intent score higher
  than "just exploring."
- **Financing** carries lighter weight — ready cash or a sanctioned loan indicates
  readiness.

The total score is bucketed into **Hot**, **Warm**, or **Cold** tiers so employees
can prioritize the strongest leads first.

## What do the lead statuses mean?

A lead moves through a lifecycle:

- **New** — just created, not yet engaged.
- **Qualifying** — currently answering the agent's questions.
- **Qualified** — completed qualification and has been scored.
- **Assigned** — allocated to an employee for follow-up.
- **Closed** — the lead has been resolved (won, lost, or dropped).

## How are leads assigned to employees?

After a lead is qualified and scored, LeadLoop automatically assigns it to an
employee. The assignment is recorded so there is a clear owner for every lead, and
the assigned employee sees the lead on their dashboard. Each lead stores its assigned
employee, and each employee can see the list of leads assigned to them.

## How does the follow-up feature work?

LeadLoop tracks each lead's last activity time. If a lead has **no activity for 2
days**, a scheduled background job:

1. Identifies the idle lead.
2. Uses the AI to **draft a follow-up email** tailored to the lead's context.
3. Stores the draft and **notifies the assigned employee**.

The employee then reviews the draft in the dashboard and can **approve, edit, or
send** it. This keeps leads warm without requiring employees to remember to follow
up manually.

## Does LeadLoop send follow-up emails automatically without human review?

No. Follow-up emails are **drafted** by the AI but are **not sent automatically**.
The assigned employee always reviews the draft and chooses to approve, edit, or send
it from the dashboard. This keeps a human in the loop for all outbound communication,
ensuring quality and avoiding unwanted automated emails.

## What can an employee do from the dashboard?

From the dashboard, an employee can:

- See the **leads assigned** to them with their tier (Hot/Warm/Cold) and status.
- Review a lead's **qualification answers** and conversation history.
- View **AI-drafted follow-up emails** for idle leads.
- **Approve, edit, or send** those follow-ups.

Admins additionally manage employees and can oversee all leads.

## What is the difference between an employee and an admin in LeadLoop?

LeadLoop has two roles:

- **Employee** — handles assigned leads, reviews and sends follow-ups.
- **Admin** — has all employee capabilities plus management functions such as
  creating employee accounts and overseeing the full lead pipeline.

Roles are enforced through authenticated access, so users only see and do what their
role permits.

## Does LeadLoop have a knowledge base / RAG chat?

Yes. Alongside lead qualification, LeadLoop includes a Retrieval-Augmented
Generation (RAG) chat. Documents (such as real-estate FAQs) are uploaded and
ingested: the text is extracted, split into chunks, embedded, and stored in a vector
database. When a user asks a question, the system retrieves the most relevant chunks
and has the LLM answer using **only** that context, citing the source passages. If
the answer is not in the knowledge base, the assistant says it doesn't have that
information rather than inventing an answer.

## How does document ingestion work in LeadLoop?

When a document is uploaded it is queued for background processing:

1. **Extract** — the file (PDF, DOCX, TXT, etc.) is converted to markdown text.
2. **Chunk** — the text is split into heading-aware sections, with large sections
   further split into overlapping token windows so context is preserved.
3. **Embed** — each chunk is turned into a vector using the configured embedding
   model.
4. **Store** — chunks and vectors are saved to the vector-enabled database.

The document's status moves through **pending → processing → ready**, or **failed**
if an error occurs (with the error recorded for troubleshooting).

## Which AI providers does LeadLoop support?

LeadLoop supports pluggable providers for both chat and embeddings, selected by
configuration. It ships with support for **OpenAI** and **Gemini**. For OpenAI, a
single API key covers both chat completions and embeddings. The embedding model and
its vector dimension must stay consistent with the database column size — switching
embedding models requires re-embedding existing documents.

## Why might the RAG chat answer "I don't have that information"?

The chat is deliberately grounded: it answers using only retrieved context. It will
say it doesn't have the information when either (a) no document in the knowledge base
covers the question, or (b) the retrieved chunks don't contain the specific answer.
This prevents the model from fabricating details. The fix is to ingest a document
that actually contains the needed content, and to phrase questions with concrete
terms so retrieval surfaces the most relevant chunk.
