import pandas as pd
import re
import time
from deep_translator import GoogleTranslator

# Read CSV
df = pd.read_csv("results.csv")

translator = GoogleTranslator(source="auto", target="en")

# Detect Hindi characters
hindi_pattern = re.compile(r'[\u0900-\u097F]')

# Convert Hindi numbers to English numbers
digit_map = str.maketrans(
    "०१२३४५६७८९",
    "0123456789"
)

# Cache translations
cache = {}

def translate_text(text):
    if pd.isna(text):
        return text

    text = str(text).strip()

    # Convert Hindi digits
    text = text.translate(digit_map)

    # Skip if no Hindi letters remain
    if not hindi_pattern.search(text):
        return text

    # Return cached translation
    if text in cache:
        return cache[text]

    try:
        translated = translator.translate(text)
        translated = translated.translate(digit_map)
        cache[text] = translated
        time.sleep(0.2)  # Prevent rate limiting
        return translated

    except Exception:
        return text

print("Starting translation...")

for column in df.columns:
    print(f"Translating {column}...")
    df[column] = df[column].apply(translate_text)

df.to_csv("results_english.csv", index=False)

print("Translation complete!")
print("Saved as results_english.csv")