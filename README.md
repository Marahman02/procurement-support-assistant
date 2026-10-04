# Procurement Support Assistant

A small retrieval-augmented (RAG) assistant for blocked supplier invoices. You describe a problem, it finds similar past tickets, Claude suggests likely causes and fix steps with the source tickets cited, and a person reviews and approves a draft report.

All data in this project is **synthetic** (made up). It is a demo of the pattern, not a product, and it has no real users.

**Live demo:** PASTE-YOUR-STREAMLIT-LINK-HERE

To try it, paste your own Anthropic API key into the sidebar. The key is used for your session only and is never stored.

## The problem

When a company buys from suppliers, three records should agree before a bill is paid: the purchase order (what was ordered), the goods receipt (what arrived) and the invoice (the supplier's bill). When they do not agree, the invoice is blocked until someone finds out why. Similar problems were usually solved before, but the answers sit in scattered old tickets.

## How it works

1. **Search.** Each of 40 synthetic tickets is turned into an embedding (a list of numbers that stands for its meaning) using ChromaDB's default model, `all-MiniLM-L6-v2`, which runs locally. The incident you type is embedded the same way, and the 3 closest tickets come back with a similarity score.
2. **Cutoff.** If the best score is below 0.40, the app says no similar cases exist and does not call the model.
3. **Answer.** Claude (`claude-sonnet-4-6`) receives the incident and the 3 tickets. It is told to use only those tickets, cite their IDs, and say so if none fit. It replies in JSON with root causes, resolution steps and a draft report.
4. **Checks.** The code strips code fences, validates the JSON, and removes any cited ticket ID that was not among the retrieved tickets. Failures show as errors and are never shown as a clean result.
5. **Approval.** The draft is editable. Nothing can be downloaded until a person clicks Approve, which also locks the text.

## What it does in practice

| Input | What happens |
|---|---|
| Invoice blocked, price 8 percent above the purchase order | Similar tickets found, two causes suggested citing TKT-001 and TKT-003, fix steps and a draft report |
| The cafeteria coffee machine is broken | Best score 0.22, below the cutoff, so no model call and "closest tickets, none relevant" |
| Employee expense report rejected for missing receipt | Passes the cutoff (0.57), then Claude says no past ticket applies. No causes, no Approve button |
| No API key entered | Clear message asking for the key in the sidebar |

The first three were run locally. On the deployed app, the expense report case and the missing-key message were confirmed.

## Testing the search

`retrieval_test.py` runs 12 queries from `queries.json`, each with the ticket that should come back, and reports how often it appears in the top 3.

- Right ticket in the top 3: **11 of 12**. Ranked first: **7 of 12**.
- The 12 queries cover all six pairs of look-alike tickets (identical symptom, different cause).
- The one miss: "we ordered by the carton but they billed per single item" expected TKT-026, whose text says "boxes of 10" and "single piece". The search model did not connect the different words.
- I tried making that ticket's symptom clearer. It did not help, so I reverted it and kept the miss as a known weakness. A stronger fix would be re-ranking or combining keyword and semantic search.

**How much to trust this:** the data is synthetic and the queries were drafted with AI help, so they match the tickets more neatly than real messages would. Twelve queries are a sanity check, not an accuracy figure. Only 12 of the 40 tickets are the target of a query.

## Limitations

- It only knows the 40 synthetic tickets. If the right answer is not there, it cannot find it.
- The 0.40 cutoff is a judgment call between the scores of unrelated queries (0.07 to 0.22) and real ones (best matches 0.50 to 0.74). It rests on a small sample and would need retuning on real data. It also cannot separate similar wording from the same problem, which is why the model-level check exists.
- Similar-sounding problems with different causes can be confused.
- Claude's output varies between runs, which is one reason a person approves every draft.
- Drafts can overstate certainty, for example saying a past case happened "under the same circumstances". Review before approving.

## Run it locally

Requires Python 3.11 (the version it was tested on).

```
git clone https://github.com/Marahman02/procurement-support-assistant.git
cd procurement-support-assistant
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
streamlit run app.py
```

Paste your Anthropic key into the sidebar, or set the `ANTHROPIC_API_KEY` environment variable before starting. The first run downloads the embedding model (about 80 MB), so it pauses for a minute.

Run the search test:

```
python retrieval_test.py
```

## Files

| File | Purpose |
|---|---|
| `app.py` | Streamlit page: key box, incident box, results, editable draft, Approve and download |
| `assistant.py` | Cutoff, prompt, model call, JSON parsing and citation check |
| `retriever.py` | Builds the ChromaDB index and searches it |
| `data/tickets.json` | The 40 synthetic tickets across 8 problem types |
| `queries.json` | The 12 test queries and their expected tickets |
| `retrieval_test.py` | Runs the queries and reports hit rate at 3 |
| `requirements.txt` | chromadb, anthropic, streamlit |

## Built with

Python, ChromaDB, the Anthropic API and Streamlit. The code was written with Claude Code from prompts I gave it in small steps. I designed the approach, ran and checked each step, and deployed it. The tickets were generated with Claude Code from a written specification, and they use general procurement terms only.

## Author

Mohammed Abdur Rahman. [GitHub](https://github.com/Marahman02) | [LinkedIn](https://www.linkedin.com/in/abdur-rahmanmohd)
