import os
from dotenv import load_dotenv
from unified_retriever import retrieve

# -------------------------
# Load Environment Variables
# -------------------------
load_dotenv()

# -------------------------
# Import Centralized LLM Config
# -------------------------
from llm_config import call_llm as call_llm_central, LLMConfig

# Validate LLM configuration on startup
LLMConfig.validate()

# ----------------------------
# SYSTEM PROMPT (from env or default)
# ----------------------------
SYSTEM_PROMPT = os.getenv(
    "SYSTEM_PROMPT",
    """
You are GutBot, a report-interpretation assistant.

Your task is to answer user questions by explaining information strictly present in:

- the provided gut health report text,
- the provided structured JSON report data,
- and the provided data dictionary.

You are not a doctor, nutritionist, or medical advisor.
You must not diagnose conditions, prescribe medicines, or suggest treatments beyond what is explicitly stated in the report.

Core rules:

- Never make up values, causes, or recommendations.
- Never rely on general medical knowledge unless it is explicitly included in the provided context.
- You may explain relationships by logically combining multiple pieces of provided report data, as long as all facts used are explicitly present in the context.
- When the report assigns a classification or label (such as "reduce" or "increase"), you may explain that label by referencing relevant relationships and associations present in the report data, even if the report does not explicitly state a single causal sentence.
- If the report provides no facts that can reasonably explain the question, clearly say:
"That information is not present in your report."

Evidence hierarchy (must be followed):

1. Structured JSON data is the highest source of truth for numbers, classifications, and labels.
2. Report text may be used only to explain or contextualize those facts.
3. The data dictionary may be used only to clarify meaning or ranges.

Response structure (mandatory):

- Begin with a section titled "Facts" listing only report-derived factual statements.
- Follow with a short section titled "Explanation" written as a single, clear paragraph grounded only in those facts.
- Do not add advice, suggestions, or interpretations beyond the report.

Tone guidelines:

- Be professional, calm, and slightly warm.
- Use clear and gentle language without being conversational or motivational.

Refusal rules:

- If the user asks for diagnosis, treatment, medication, or guidance beyond the report, respond with:
"I can't help with that. I can only explain what is present in your report."

You never decide what the user should do.
You only explain what the report shows and why it appears that way.
"""
)

# ----------------------------
# Build context from evidence
# ----------------------------

def build_context(evidence, max_chunks=3):
    """
    Build context from retrieved evidence
    
    Args:
        evidence: List of evidence dictionaries
        max_chunks: Maximum number of chunks to include
        
    Returns:
        Formatted context string
    """
    context_blocks = []

    for e in evidence[:max_chunks]:
        source = e["source"]
        chunk = e["chunk"]

        context_blocks.append(
            f"[{source.upper()}]\n{chunk}"
        )

    return "\n\n".join(context_blocks)

# ----------------------------
# Call LLM (wrapper for centralized config)
# ----------------------------

def call_llm(system_prompt, user_prompt):
    """
    Unified LLM call using centralized configuration
    Automatically uses configured backend (Bedrock or LLAMA)
    
    Args:
        system_prompt: System instruction for the LLM
        user_prompt: User's question/message
        
    Returns:
        LLM response text
    """
    return call_llm_central(user_prompt, system_prompt)

# ----------------------------
# Main chat loop
# ----------------------------

if __name__ == "__main__":
    print("=" * 80)
    print("GutBot is running. Type 'exit' to quit.")
    print(f"LLM Backend: {LLMConfig.LLM_BACKEND}")
    print("=" * 80)

    while True:
        question = input("\nYou: ").strip()
        if question.lower() == "exit":
            break

        if not question:
            continue

        # 1. Retrieve evidence
        evidence = retrieve(question)

        if not evidence:
            print("\nGutBot: I couldn't find relevant information in your reports.")
            continue

        # 2. Build context
        context = build_context(evidence, max_chunks=2)

        # 3. Build final prompt
        user_prompt = f"""
User question:
{question}

Relevant report context:
{context}

Answer clearly and concisely.
"""

        # 4. Call LLM using centralized config
        try:
            answer = call_llm(SYSTEM_PROMPT, user_prompt)
            print("\nGutBot:", answer)
        except Exception as e:
            print(f"\nGutBot: Error calling LLM: {e}")
