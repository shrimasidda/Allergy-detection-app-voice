"""
Allergy Detection Project — Streamlit App with EasyOCR
======================================================
This version uses EasyOCR for OCR on images, so it works fully on Streamlit Cloud without needing Tesseract installation.

How to run:
1. Upload `allergy_app.py` and `requirements.txt` to a GitHub repo.
2. Deploy on Streamlit Cloud.
"""

import streamlit as st
import csv
import json
import easyocr
import cv2
from PIL import Image
import numpy as np
from pathlib import Path

DB_CSV = 'ingredients_db.csv'
USER_JSON = 'user_profile.json'

SAMPLE_DB = [
    {"food": "Peanut Butter Sandwich", "ingredients": "peanut, wheat flour, salt, sugar, vegetable oil"},
    {"food": "Caesar Salad", "ingredients": "lettuce, parmesan, anchovy, egg, olive oil, lemon"},
    {"food": "Strawberry Yogurt", "ingredients": "milk, strawberry, sugar, pectin"},
    {"food": "Paneer Butter Masala", "ingredients": "milk, paneer, tomato, butter, cashew"},
    {"food": "Sushi (California Roll)", "ingredients": "rice, avocado, crab (surimi), seaweed, sesame"},
]

reader = easyocr.Reader(['en'])


def ensure_db():
    if not Path(DB_CSV).exists():
        with open(DB_CSV, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=['food', 'ingredients'])
            writer.writeheader()
            for row in SAMPLE_DB:
                writer.writerow(row)


def load_db():
    ensure_db()
    with open(DB_CSV, newline='', encoding='utf-8') as f:
        return list(csv.DictReader(f))


def save_food(food, ingredients):
    with open(DB_CSV, 'a', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=['food', 'ingredients'])
        writer.writerow({'food': food, 'ingredients': ingredients})


def load_user():
    if not Path(USER_JSON).exists():
        with open(USER_JSON, 'w', encoding='utf-8') as f:
            json.dump({'name': 'default', 'allergies': []}, f)
    with open(USER_JSON, encoding='utf-8') as f:
        return json.load(f)


def save_user(profile):
    with open(USER_JSON, 'w', encoding='utf-8') as f:
        json.dump(profile, f, indent=2)


def normalize(s):
    return s.strip().lower()


def parse_ingredients(text):
    return {normalize(x) for x in text.replace(';', ',').split(',') if x.strip()}


def check_allergy(profile, ingredients_text):
    user_allergies = {normalize(a) for a in profile.get('allergies', [])}
    food_ings = parse_ingredients(ingredients_text)
    direct = user_allergies.intersection(food_ings)
    partial = set()
    for ua in user_allergies:
        for fi in food_ings:
            if ua in fi and ua != fi:
                partial.add(fi)
    severity = 'High' if direct else 'Medium' if partial else 'Low'
    return {
        'ingredients': sorted(food_ings),
        'direct': sorted(direct),
        'partial': sorted(partial),
        'severity': severity
    }


def extract_text_from_image(image: Image.Image):
    img = np.array(image.convert('RGB'))
    results = reader.readtext(img, detail=0)
    return ', '.join(results)


# Streamlit UI
st.set_page_config(page_title="Allergy Detection App", page_icon="🥗", layout="centered")
st.title("📸 Smart Allergy Detection System")

menu = st.sidebar.radio("Menu", ["Home", "Scan Label", "Add Food", "Manage Allergies"])
profile = load_user()
db = load_db()

if menu == "Home":
    st.markdown("### Welcome to Smart Allergy Detection!")
    st.write("Scan or upload a food label to detect allergens.")
    st.markdown("#### Quick Steps:")
    st.write("1️⃣ Go to **Scan Label** and use your camera.")
    st.write("2️⃣ The app extracts text from the image.")
    st.write("3️⃣ It checks the detected ingredients against your allergy profile.")

elif menu == "Scan Label":
    st.subheader("📷 Scan or Upload Food Label")
    uploaded_image = st.camera_input("Take a photo of the label") or st.file_uploader("Or upload an image", type=["jpg", "jpeg", "png"])

    if uploaded_image:
        image = Image.open(uploaded_image)
        st.image(image, caption="Uploaded Image", use_container_width=True)

        with st.spinner('Extracting ingredients from image...'):
            text = extract_text_from_image(image)

        st.text_area("Extracted Text:", text, height=150)

        if st.button("Check for Allergies"):
            res = check_allergy(profile, text)
            st.write(f"**Your Allergies:** {', '.join(profile['allergies']) or 'None'}")
            st.write(f"**Detected Ingredients:** {', '.join(res['ingredients'])}")
            st.write(f"**Direct Matches:** {', '.join(res['direct']) or 'None'}")
            st.write(f"**Partial Matches:** {', '.join(res['partial']) or 'None'}")
            st.warning(f"**Severity Level:** {res['severity']}")

elif menu == "Add Food":
    st.subheader("Add a New Food")
    name = st.text_input("Food Name")
    ingredients = st.text_area("Ingredients (comma-separated)")
    if st.button("Add Food"):
        if name and ingredients:
            save_food(name, ingredients)
            st.success(f"Added {name} to database!")
        else:
            st.error("Please enter both food name and ingredients.")

elif menu == "Manage Allergies":
    st.subheader("Manage Your Allergy Profile")
    allergies = profile.get('allergies', [])
    st.write("### Current Allergies:")
    st.write(', '.join(allergies) if allergies else 'No allergies yet.')

    new_allergy = st.text_input("Add a new allergy:")
    if st.button("Add Allergy"):
        if new_allergy:
            allergies.append(normalize(new_allergy))
            profile['allergies'] = sorted(set(allergies))
            save_user(profile)
            st.success(f"Added {new_allergy}!")

    remove = st.selectbox("Remove an allergy", ['None'] + allergies)
    if st.button("Remove Allergy") and remove != 'None':
        profile['allergies'] = [a for a in allergies if a != remove]
        save_user(profile)
        st.warning(f"Removed {remove}.")
