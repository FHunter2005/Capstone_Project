def elaboration_prompt(master_doc: dict, user_query: str) -> str:
    about_text = master_doc.get("about", "No description available.")
    return f"""
You are an expert educational advisor. A user asked: '{user_query}'.

Based on the following program information, provide a detailed, engaging and natural explanation:

Master Program: {master_doc.get('master')}
University: {master_doc.get('university')}
Location: {master_doc.get('Location', 'Not available')}
Duration: {master_doc.get('Duration', 'Not available')}
Tuition Fee: {master_doc.get('Tuition Fee', 'Not available')}
About: {about_text}
"""
