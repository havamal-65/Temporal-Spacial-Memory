import os
import glob
import json
from tqdm import tqdm
from PyPDF2 import PdfReader
from src.models.polar_temporal import PolarTemporalSpace
from langchain_openai import ChatOpenAI
from langchain.chains import MapReduceDocumentsChain, ReduceDocumentsChain, LLMChain, StuffDocumentsChain
from langchain.prompts import PromptTemplate
from langchain_core.documents import Document
import time

# Define the main stages for the overall progress bar
main_stages = [
    "PDF Discovery",
    "Text Extraction",
    "Fragment Processing",
    "Embedding/Indexing",
    "LangChain Doc Preparation",
    "LLM Summarization",
    "Output Writing"
]

with tqdm(total=len(main_stages), desc="Overall Progress", bar_format='{l_bar}{bar}| {n_fmt}/{total_fmt} [{elapsed}<{remaining}] {desc}') as overall_pbar:
    # 1. Find the first PDF in the input directory
    input_dir = "input"
    output_dir = "output"
    print(f"[INFO] Searching for PDF files in '{input_dir}' directory...")
    pdf_files = glob.glob(os.path.join(input_dir, "*.pdf"))
    if not pdf_files:
        raise FileNotFoundError("No PDF files found in the input directory.")
    pdf_path = pdf_files[0]
    print(f"[INFO] Processing PDF: {pdf_path}")
    overall_pbar.update(1)

    # 2. Extract text by page
    print("[INFO] Extracting text from PDF pages...")
    reader = PdfReader(pdf_path)
    pages = []
    for i, page in enumerate(tqdm(reader.pages, desc="Extracting pages", unit="page")):
        pages.append(page.extract_text() or "")
    print(f"[INFO] Extracted text from {len(pages)} pages.")
    overall_pbar.update(1)

    # 3. Process with PolarTemporalSpace
    print("[INFO] Initializing PolarTemporalSpace and fragmenting content...")
    space = PolarTemporalSpace(clustering_method='fixed_bins')
    fragments = []
    for i, text in enumerate(tqdm(pages, desc="Fragmenting pages", unit="page")):
        if text.strip():
            fragments.append({'text': text, 'page_number': i+1})
    print(f"[INFO] {len(fragments)} non-empty fragments/pages identified.")
    overall_pbar.update(1)

    # Feed each page as a chunk
    chunks = [frag['text'] for frag in fragments]
    print(f"[INFO] Prepared {len(chunks)} chunks for embedding and indexing.")

    # Use PolarTemporalSpace to process
    print("[INFO] Embedding and indexing pages with PolarTemporalSpace...")
    vectors = []
    for idx, frag in enumerate(tqdm(fragments, desc="Embedding/Indexing", unit="frag")):
        vectors.extend(space.process_content(frag['text'], content_type='pdf', metadata={'page_number': frag['page_number']}))
        if (idx + 1) % 10 == 0 or (idx + 1) == len(fragments):
            tqdm.write(f"[DEBUG] Processed {idx + 1}/{len(fragments)} fragments.")
    overall_pbar.update(1)

    # 4. Prepare LangChain documents for summarization
    print("[INFO] Preparing LangChain documents for summarization...")
    lc_docs = [Document(page_content=chunk, metadata={"page_number": i+1}) for i, chunk in enumerate(tqdm(chunks, desc="Preparing LangChain Docs", unit="chunk"))]
    overall_pbar.update(1)

    # 5. Manual Map-Reduce with Progress Bar for Summarization
    print("[INFO] Setting up LLM summarization chains (manual map-reduce)...")
    llm = ChatOpenAI(temperature=0)
    map_prompt = PromptTemplate.from_template("""The following is a set of documents\n{docs}\nBased on this list of docs, please identify the main themes\nHelpful Answer:""")
    map_chain = LLMChain(llm=llm, prompt=map_prompt)
    reduce_prompt = PromptTemplate.from_template("""The following is set of summaries:\n{doc_summaries}\nTake these and distill it into a final, consolidated summary of the main themes.\nHelpful Answer:""")
    reduce_chain = LLMChain(llm=llm, prompt=reduce_prompt)

    print("[INFO] Summarizing with LLM (map step, per chunk)...")
    map_summaries = []
    map_start_time = time.time()
    for i, doc in enumerate(tqdm(lc_docs, desc="LLM Map Step", unit="chunk")):
        # Each doc is a LangChain Document; pass its content to the map_chain
        map_result = map_chain.invoke({"docs": doc.page_content})
        # Handle both dict and string outputs
        if isinstance(map_result, dict) and "text" in map_result:
            map_summaries.append(map_result["text"])
        else:
            map_summaries.append(str(map_result))
    map_time = time.time() - map_start_time
    print(f"[INFO] Map step complete in {map_time:.1f} seconds.")

    # Reduce step (single call, but time it)
    print("[INFO] Reducing summaries to final summary...")
    reduce_input = "\n".join(map_summaries)
    reduce_start_time = time.time()
    final_summary = reduce_chain.invoke({"doc_summaries": reduce_input})
    reduce_time = time.time() - reduce_start_time
    print(f"[INFO] Reduce step complete in {reduce_time:.1f} seconds.")

    # Use final_summary as your summary
    summary = final_summary["text"] if isinstance(final_summary, dict) and "text" in final_summary else str(final_summary)
    overall_pbar.update(1)

    # 6. Output results
    print(f"[INFO] Writing summary to '{output_dir}/summary.txt'...")
    os.makedirs(output_dir, exist_ok=True)
    with open(os.path.join(output_dir, "summary.txt"), "w", encoding="utf-8") as f:
        f.write(summary)
    print(f"[INFO] Writing chunks to '{output_dir}/chunks.txt'...")
    with open(os.path.join(output_dir, "chunks.txt"), "w", encoding="utf-8") as f:
        for i, chunk in enumerate(tqdm(chunks, desc="Writing Chunks", unit="chunk")):
            f.write(f"--- Page {i+1} ---\n{chunk}\n\n")
    print(f"[INFO] Writing node metadata to '{output_dir}/nodes.json'...")
    # Output node metadata
    node_list = [
        {
            "content": v.content[:100],
            "distance": v.distance,
            "angle": v.angle,
            "time_position": v.time_position,
            "metadata": v.metadata
        }
        for v in tqdm(space.all_vectors, desc="Writing Node Metadata", unit="node")
    ]
    with open(os.path.join(output_dir, "nodes.json"), "w", encoding="utf-8") as f:
        json.dump(node_list, f, indent=2)
    print(f"[SUCCESS] Summary, chunks, and node metadata written to '{output_dir}' folder.")
    overall_pbar.update(1) 