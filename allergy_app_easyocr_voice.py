"""
Allergy Detection Project — Duplicate with Voice Recognition
============================================================
Features:
1. Multiple user profiles stored in `user_profile.json`
2. Voice recognition login (recognizes user by voice)
3. OCR-based ingredient detection using EasyOCR
4. Allergy check for the recognized user
"""

import streamlit as st
import csv
import json
import easyocr
import cv2
from PIL import Image
import numpy as np
from pathlib import Path

# For voice recognition
import speech_recognition as sr

# ---------- File paths ----------
DB_CSV = 'ingredients_db.csv'
USER_JSON = 'user_profile.json'

# ---------- Sample database ----------
SAMPLE_DB = [
    {"food": "Peanut Butter Sandwich", "ingredients": "peanut, wheat flour, salt, sugar, vegetable oil"},
    {"food": "Caesar Salad", "ingredients": "lettuce, parmesan, anchovy, egg, olive oil, lemon"},
    {"food": "Strawberry Yogurt", "ingredients": "milk, strawberry, sugar, pectin"},
    {"food": "Paneer Butter Masala", "ingredients": "milk, paneer, tomato, butter, cashew"},
    {"food": "Sushi (California Roll)", "ingredients": "rice, avocado, crab (surimi), seaweed, sesame"},
]

reader = easyocr.Reader(['en'])

# ---------- Functions ----------

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

def load_users():
    if not Path(USER_JSON).exists():
        default_profiles = {
            "users": [
                {"name": "Shrima", "allergies": ["peanut", "milk"]},
                {"name": "Teammate1", "allergies": ["egg", "wheat"]},
                {"name": "Teammate2", "allergies": ["soy"]}
            ]
        }
        with open(USER_JSON, 'w', encoding='utf-8') as f:
            json.dump(default_profiles, f, indent=2)
    with open(USER_JSON, encoding='utf-8') as f:
        return json.load(f)['users']

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

# ---------- Voice Recognition ----------
def recognize_user():
    recognizer = sr.Recognizer()
    with sr.Microphone() as source:
        st.info("🎤 Please speak your name clearly...")
        audio = recognizer.listen(source, phrase_time_limit=3)
    try:
        text = recognizer.recognize_google(audio)
        return text.lower()
    except:
        return None

def find_user_by_name(name_text, users):
    for user in users:
        if normalize(user['name']) in name_text:
            return user
    return None

# ---------- Streamlit UI ----------
st.set_page_config(page_title="Allergy Detection App", page_icon="🥗", layout="centered")
st.title("📸 Smart Allergy Detection with Voice Login")

users = load_users()
db = load_db()

# Voice login
st.sidebar.subheader("User Login")
if 'profile' not in st.session_state:
    if st.sidebar.button("Login via Voice"):
        name_detected = recognize_user()
        if name_detected:
            profile = find_user_by_name(name_detected, users)
            if profile:
                st.session_state['profile'] = profile
                st.success(f"Hello, {profile['name']}! Profile loaded successfully.")
            else:
                st.warning("User not recognized. Try again.")
        else:
            st.error("Voice not detected. Try again.")

profile = st.session_state.get('profile', None)

# Menu
menu = st.sidebar.radio("Menu", ["Home", "Scan Label", "Add Food", "Manage Allergies"])

if menu == "Home":
    st.markdown("### Welcome to Smart Allergy Detection!")
    if profile:
        st.write(f"Logged in as: **{profile['name']}**")
    st.write("Scan or upload a food label to detect allergens.")
    st.markdown("#### Quick Steps:")
    st.write("1️⃣ Login using your voice in the sidebar.")
    st.write("2️⃣ Go to **Scan Label** and use your camera.")
    st.write("3️⃣ Check allergens automatically for your profile.")

elif menu == "Scan Label":
    if not profile:
        st.warning("Please login via voice first!")
    else:
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
    if not profile:
        st.warning("Please login via voice first!")
    else:
        st.subheader("Manage Your Allergy Profile")
        allergies = profile.get('allergies', [])
        st.write("### Current Allergies:")
        st.write(', '.join(allergies) if allergies else 'No allergies yet.')

        new_allergy = st.text_input("Add a new allergy:")
        if st.button("Add Allergy"):
            if new_allergy:
                allergies.append(normalize(new_allergy))
                profile['allergies'] = sorted(set(allergies))
                # Update user_profile.json
                all_users = load_users()
                for u in all_users:
                    if u['name'] == profile['name']:
                        u['allergies'] = profile['allergies']
                with open(USER_JSON, 'w', encoding='utf-8') as f:
                    json.dump({"users": all_users}, f, indent=2)
                st.success(f"Added {new_allergy}!")

        remove = st.selectbox("Remove an allergy", ['None'] + allergies)
        if st.button("Remove Allergy") and remove != 'None':
            profile['allergies'] = [a for a in allergies if a != remove]
            all_users = load_users()
            for u in all_users:
                if u['name'] == profile['name']:
                    u['allergies'] = profile['allergies']
            with open(USER_JSON, 'w', encoding='utf-8') as f:
                json.dump({"users": all_users}, f, indent=2)
            st.warning(f"Removed {remove}.")
