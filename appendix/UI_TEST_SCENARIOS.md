# Personal Research Portal — UI Test Scenarios

Run the app with `./run_app.sh`, then follow these scenarios in order.

---

## Scenario 1: Search & Ask (Core Flow)

**Goal:** Verify the main research query flow works end-to-end.

1. **Land on Search & Ask** (default page)
   - [ ] Page shows "Research Query" heading
   - [ ] Query input has placeholder: "What are the advantages of small language models?"
   - [ ] "Ask" button is visible (primary/navy)
   - [ ] Retrieval Filters are in a collapsed expander

2. **Submit a query**
   - [ ] Type: `What is Phi-3's performance on MMLU?`
   - [ ] Click **Ask**
   - [ ] Spinner appears: "Retrieving evidence from X sources..."
   - [ ] Spinner disappears; answer panel appears with gold left border
   - [ ] Answer contains inline citations (e.g. `[Source: Phi3_2024, Chunk: ...]`)
   - [ ] Status strip below answer shows GROUNDED / PARTIALLY GROUNDED / NOT GROUNDED
   - [ ] "Retrieved Evidence" section shows evidence cards with source_id, chunk_id, relevance score

2a. **Verify evidence (what to look for)**
   - [ ] **Hint above cards**: "Match citations in the answer (e.g. Phi3_2024, Phi3_2024_chunk_0001) to the source_id · chunk_id in each card header."
   - [ ] **CITED IN ANSWER** badge — cards that support claims in the answer show this green badge; cited cards appear first (in citation order)
   - [ ] Each card shows a **text snippet** — does it contain the specific facts the answer cites? (e.g. for "Phi-3-mini achieves X% on MMLU", the cited chunk should show the MMLU row with numbers)
   - [ ] **Relevance score** — green (>0.8) = highly relevant; amber (0.5–0.8) = moderate; red (<0.5) = weak
   - [ ] **Source metadata** — authors, year, venue — confirms you're looking at the right paper
   - [ ] If the answer cites a chunk but the snippet shows only preamble (no table values, no numbers), the evidence may support the claim but the snippet may be truncated — check the Source Library for the full chunk

3. **Verify action buttons**
   - [ ] **Save Thread** — click it; status strip shows "SAVED"
   - [ ] **Generate Artifact** — click it; navigates to Artifact Generator
   - [ ] **Copy Answer** — click it; text area appears with answer

4. **Return and check state**
   - [ ] Click **Search & Ask** in sidebar
   - [ ] Last query and results still visible (navigation preserves state)

---

## Scenario 2: Research Threads

**Goal:** Verify threads are saved and can be resumed.

1. **Navigate to Research Threads**
   - [ ] Click **Research Threads** in sidebar
   - [ ] If you saved a thread in Scenario 1: thread card appears with query preview, timestamp, sources cited
   - [ ] If no threads: empty state "No saved threads yet. Use 'Save Thread'..."

2. **View a thread**
   - [ ] Click **View Thread** on a thread card
   - [ ] Expander opens with full query, full answer (with citation chips), evidence cards

3. **Resume Query**
   - [ ] Click **Resume Query**
   - [ ] App navigates to Search & Ask
   - [ ] Query input is pre-filled with the thread's query
   - [ ] (Optional) Click Ask to re-run with same query

4. **Export All Threads**
   - [ ] Click **Export All Threads**
   - [ ] Markdown file downloads

---

## Scenario 3: Artifact Generator

**Goal:** Generate and export research artifacts.

1. **Navigate to Artifact Generator**
   - [ ] Click **Artifact Generator** in sidebar
   - [ ] If you came from Search & Ask via "Generate Artifact": caption shows "Based on your query: ..."
   - [ ] Research question field is pre-filled (if applicable)

2. **Generate Evidence Table**
   - [ ] Select **Evidence Table**
   - [ ] Enter research question (or use prefill)
   - [ ] Click **Generate Artifact**
   - [ ] Spinner: "Generating evidence table... analyzing sources"
   - [ ] Table appears with columns: Claim | Evidence | Citation | Confidence | Notes
   - [ ] Export buttons appear: Download CSV, Download Markdown, Download PDF

3. **Generate Annotated Bibliography**
   - [ ] Select **Annotated Bibliography**
   - [ ] Click **Generate Artifact**
   - [ ] Source cards appear with Key Claim, Method, Limitations, Relevance
   - [ ] Export buttons work

4. **Generate Synthesis Memo**
   - [ ] Select **Synthesis Memo**
   - [ ] Click **Generate Artifact**
   - [ ] Memo appears (800–1200 words) with inline citations
   - [ ] References section at end
   - [ ] Export works

---

## Scenario 4: Evaluation Dashboard

**Goal:** Run evaluation and review metrics.

1. **Navigate to Evaluation Dashboard**
   - [ ] Click **Evaluation Dashboard** in sidebar

2. **If no prior run**
   - [ ] Empty state: "No evaluation runs yet. Click 'Run Evaluation'..."
   - [ ] Single **Run Evaluation** button (primary)

3. **Run evaluation**
   - [ ] Click **Run Evaluation**
   - [ ] Progress bar appears: "Running evaluation set... 1/25 queries complete"
   - [ ] Progress updates as each query runs
   - [ ] When done: 4 metric cards appear (Groundedness, Citation Precision, Relevance, Query Count)
   - [ ] Metric values are color-coded (green > 0.7, amber 0.5–0.7, red < 0.5)

4. **Review results**
   - [ ] "Per-Query Results" table is sortable
   - [ ] "Representative Failure Cases" shows 3+ failure cards (red left border)
   - [ ] Each failure card has: query, tag (e.g. MISSING EVIDENCE), what went wrong, retrieved vs answer, suggested fix

5. **Export Report**
   - [ ] Click **Export Report**
   - [ ] Markdown file downloads

---

## Scenario 5: Source Library

**Goal:** Browse and filter the corpus.

1. **Navigate to Source Library**
   - [ ] Click **Source Library** in sidebar
   - [ ] Header shows "X sources"
   - [ ] Caption: "X sources · Y chunks"

2. **Filters**
   - [ ] Expand Filters
   - [ ] Search by keyword, filter by source type, filter by year
   - [ ] Cards update when filters change

3. **Source cards**
   - [ ] Each card shows: authors (year), title, venue, type, ID, relevance note, chunk count
   - [ ] **View Chunks** button expands chunk previews
   - [ ] **Open Source** button (enabled if URL exists)

---

## Scenario 6: Export Center

**Goal:** Download saved artifacts and reports.

1. **Navigate to Export Center**
   - [ ] Click **Export Center** in sidebar
   - [ ] Caption: "Download research artifacts, evaluation reports, and thread exports."

2. **If files exist**
   - [ ] **Research Artifacts** section lists files from `outputs/artifacts/`
   - [ ] **Evaluation Reports** section lists files from `logs/eval_runs/` or `outputs/`
   - [ ] **Research Threads** section lists files from `outputs/threads/`
   - [ ] Each file has a **Download** button
   - [ ] Files sorted by most recent first

3. **If no files**
   - [ ] Empty state: "No exports available. Generate artifacts or run evaluations..."

---

## Scenario 7: Trust Behaviors

**Goal:** Verify trust behaviors (citations, missing evidence, fabricated citation handling).

1. **Query with good evidence**
   - [ ] Ask: `What is Phi-3's parameter count?`
   - [ ] Answer has citations; status strip shows GROUNDED or PARTIALLY GROUNDED

2. **Query with no evidence**
   - [ ] Ask: `What is the capital of France?` (or something outside corpus)
   - [ ] Status strip: "No relevant evidence found... Consider rephrasing or broadening your search terms."
   - [ ] No answer generated (or explicit "insufficient information" message)

3. **Partial evidence**
   - [ ] Use a query that returns few citations
   - [ ] Amber warning appears: "Some claims in this answer may not be fully supported..."
   - [ ] Status strip shows PARTIALLY GROUNDED or NOT GROUNDED

---

## Scenario 8: Navigation & State

**Goal:** Verify cross-page flows and state preservation.

1. **Generate Artifact from Search & Ask**
   - [ ] Run a query on Search & Ask
   - [ ] Click **Generate Artifact**
   - [ ] Artifact Generator opens with query and evidence pre-filled
   - [ ] Caption shows "Based on your query: ..."

2. **Resume Query from Threads**
   - [ ] Go to Research Threads
   - [ ] Click **Resume Query** on a thread
   - [ ] Search & Ask opens with query pre-filled
   - [ ] Click Ask to re-run

3. **State preservation**
   - [ ] Run a query on Search & Ask
   - [ ] Navigate to Source Library, then back to Search & Ask
   - [ ] Last query and results still visible

---

## Quick Smoke Test (5 min)

If time is limited, run this minimal set:

1. Ask a question → verify answer + citations + evidence cards
2. Save Thread → verify it appears in Research Threads
3. Generate Artifact (Evidence Table) → verify table + export
4. Run Evaluation → verify progress bar + metric cards
5. Export Center → verify download buttons work
