# advisor_chat.py
import pandas as pd
from google import genai

def load_data(master_path, location_path):
    df_masters = pd.read_csv(master_path)
    df_locations = pd.read_csv(location_path, sep=";", usecols=[0, 1], engine="python", on_bad_lines="skip")
    df_locations.columns = ["Institution", "GoogleMaps"]
    return df_masters, df_locations

def build_website_knowledge(df_masters, df_locations):
    masters_knowledge = ""
    for _, row in df_masters.iterrows():
        masters_knowledge += (
            f"Program: {row['master']}\n"
            f"University: {row['university']}\n"
            f"Location: {row['Location']}\n"
            f"Duration: {row['Duration']}\n"
            f"Tuition: {row['Tuition Fee']}\n"
            f"About: {row['about']}\n"
        )

    location_knowledge = ""
    for _, row in df_locations.iterrows():
        location_knowledge += f"Institution: {row['Institution']} | GoogleMaps: {row['GoogleMaps']}\n"

    return (
        "Masters Programs:\n" + masters_knowledge + "\n" +
        "Universities and Locations:\n" + location_knowledge
    )

def system_instruction(website_knowledge: str) -> str:
    return f"""
You are a professional Master's degree advisor.

You have access to the following structured knowledge:

========================
{website_knowledge}
========================

Rules:
- ALWAYS base recommendations only on the knowledge above.
- Provide 5 recommendations.
- For each master's program, ALWAYS include in this order:
    1. Program name
    2. Institution
    3. Location (city)
- Give clear, helpful, personalized suggestions.
- If they ask for location, use the GoogleMaps links provided.
- If they ask for more info about a program, give them what is in the knowledge base.
"""


