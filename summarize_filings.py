import os
from dotenv import load_dotenv
import sys
if not os.path.exists('.env'):
    print("Error: .env file not found. Please create a .env file with your OPENAI_API_KEY.")
    sys.exit(1)
load_dotenv()
import json
from langchain_openai import ChatOpenAI
from langchain_core.documents import Document
from langchain_classic.text_splitter import RecursiveCharacterTextSplitter
from langchain_classic.chains.summarize import load_summarize_chain


# Load your text (T-Mobile 10-K)
FILING_PATH = "0001283699/000128369924000008.tar__tmus-20231231.htm.json"

with open(FILING_PATH) as f:
    data = json.load(f)
text = data.get("text", str(data))

text_splitter = RecursiveCharacterTextSplitter(chunk_size=2000, chunk_overlap=200)
chunks = text_splitter.split_text(text)

# --- Focus on cybersecurity-related chunks ---
keywords = [
    "cyber", "security", "breach", "data breach", "data", "hack", "hacked", "incident",
    "ransom", "phish", "phishing", "vulnerability", "intrusion", "malware", "privacy",
    "incident response", "security incident", "cybersecurity", "security program"
]

def contains_keywords(s: str, kws=keywords):
    low = s.lower()
    return any(k in low for k in kws)

selected_chunks = [c for c in chunks if contains_keywords(c)]
if not selected_chunks:
    print("No cybersecurity-specific chunks found; falling back to entire document.")
    selected_chunks = chunks

# Create documents from selected chunks
docs = [Document(page_content=chunk) for chunk in selected_chunks]

llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
summary_chain = load_summarize_chain(llm, chain_type="map_reduce")

import time
print(f"Total chunks to process: {len(docs)}")
start_time = time.time()

for i, doc in enumerate(docs, 1):
    chunk_start = time.time()
    print(f"\nProcessing chunk {i}/{len(docs)}...")
    if i > 1:
        elapsed_time = time.time() - start_time
        avg_time_per_chunk = elapsed_time / (i - 1)
        remaining_chunks = len(docs) - i + 1
        estimated_time_left = avg_time_per_chunk * remaining_chunks
        print(f"Estimated time remaining: {estimated_time_left:.1f} seconds ({estimated_time_left/60:.1f} minutes)")

def normalize_summary(s):
    """Return a string summary from chain output (dict/list/str)."""
    if isinstance(s, dict):
        for key in ("output_text", "text", "summary", "result", "content"):
            if key in s and isinstance(s[key], str):
                return s[key]
        return json.dumps(s, ensure_ascii=False)
    if isinstance(s, list):
        return "\n".join([x if isinstance(x, str) else json.dumps(x, ensure_ascii=False) for x in s])
    return str(s)

# Process in batches so we can show real progress and ETA. Adjust batch_size to control number of LLM calls.
batch_size = 20
num_batches = (len(docs) + batch_size - 1) // batch_size
batch_summaries = []

for b in range(num_batches):
    i0 = b * batch_size
    i1 = min((b + 1) * batch_size, len(docs))
    batch_docs = docs[i0:i1]
    print(f"\nProcessing batch {b+1}/{num_batches} (chunks {i0+1}-{i1})...")
    batch_start = time.time()
    batch_summary = summary_chain.invoke(batch_docs)
    batch_summary_text = normalize_summary(batch_summary)
    batch_summaries.append(batch_summary_text)
    batch_elapsed = time.time() - batch_start
    remaining_batches = num_batches - (b + 1)
    if b >= 0:
        avg_batch = (time.time() - start_time) / (b + 1)
        eta = avg_batch * remaining_batches
        print(f"Batch took {batch_elapsed:.1f}s — estimated remaining: {eta:.1f}s ({eta/60:.1f}m)")

print("\nCombining batch summaries into final focused summary...")
# Try to extract the Item 1C (Cybersecurity) section from the raw filing text for inclusion
def extract_item_section(full_text: str, start_label: str = "item 1c", end_labels=None):
    if end_labels is None:
        end_labels = ["item 1d", "item 2", "item 1b", "item 3", "item 7"]
    lower = full_text.lower()
    start_idx = lower.find(start_label.lower())
    if start_idx == -1:
        return ""
    # find nearest end label after start_idx
    end_idx = None
    for lbl in end_labels:
        i = lower.find(lbl.lower(), start_idx + 1)
        if i != -1:
            if end_idx is None or i < end_idx:
                end_idx = i
    if end_idx is None:
        return full_text[start_idx:]
    return full_text[start_idx:end_idx]

item1c_text = extract_item_section(text, start_label="Item 1C")

# Build combine docs: first an instruction, then Item 1C (if any), then batch summaries
instruction = (
    "You are an analyst. Produce a concise but detailed structured summary focused ONLY on cybersecurity matters. "
    "Include these sections: (1) Incidents mentioned (dates, scope, monetary impact if available), "
    "(2) Controls and mitigations (technical and organizational), (3) Insurance and limitations, "
    "(4) Third-party/vendor risks and dependencies, and (5) Outstanding exposures and recommended follow-ups. "
    "Use the following text as source material; do not invent facts. If information is missing, state 'not disclosed'."
)

combine_docs = [Document(page_content=instruction)]
if item1c_text:
    combine_docs.append(Document(page_content=item1c_text))
combine_docs.extend([Document(page_content=s) for s in batch_summaries])

final_summary_obj = summary_chain.invoke(combine_docs)
summary_text = normalize_summary(final_summary_obj)

total_time = time.time() - start_time
print(f"\nTotal processing time: {total_time:.1f} seconds ({total_time/60:.1f} minutes)")

# Save the result
os.makedirs("summaries", exist_ok=True)
output_path = "summaries/tmobile_10k_summary.txt"
with open(output_path, "w") as f:
    f.write(summary_text)

print(f"\n✅ Summary saved to {output_path}")