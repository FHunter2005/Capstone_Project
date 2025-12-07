# ai/prompts.py

def multi_program_prompt(master_docs: list[dict], user_query: str) -> str:
    """
    New multi-program prompt (REPLACES the testing.py version).
    One LLM call → multiple programs → consistent formatting.
    """

    programs_text = ""
    for i, doc in enumerate(master_docs, 1):
        programs_text += (
            f"\n### Program {i}\n"
            f"Master Program: {doc.get('master')}\n"
            f"University: {doc.get('university')}\n"
            f"Location: {doc.get('Location')}\n"
            f"Duration: {doc.get('Duration')}\n"
            f"Tuition Fee: {doc.get('Tuition Fee')}\n"
            f"About: {doc.get('about', '')}\n"
        )

    return f"""
You are an educational advisor. The user asked:

**"{user_query}"**

You will receive up to 5 master's programs from a dataset that ONLY contains programs from **Portugal**.

### STRICT RULES:
- Only describe THESE programs.
- Do NOT create new universities or programs.
- Do NOT mention programs outside Portugal.
- No hallucinating tuition fees or fake details.
- Keep tone friendly but professional.

---

### For EACH program provide:
- **Master Program**
- **University**
- **Location**
- **Tuition Fee**
- **Why it could be a good fit**
- **Ideal for students who**
- **What makes it special**

---

### Programs:
{programs_text}
"""
