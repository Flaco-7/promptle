import os
import json
import requests
import io
import sys
import re
from datetime import datetime, timedelta
from openai import OpenAI
from supabase import create_client, Client
from PIL import Image
from dotenv import load_dotenv

# Charger les variables d'environnement
load_dotenv()

OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")

def is_valid_word(word):
    """Vérifie si un mot est composé uniquement de 5 à 8 lettres A-Z sans accents."""
    if not word:
        return False
    return bool(re.match(r"^[A-Z]{5,8}$", word))

def sanitize_filename(filename):
    """Nettoie le nom de fichier pour Supabase Storage."""
    n = filename.lower()
    n = re.sub(r'[éèêë]', 'e', n)
    n = re.sub(r'[àâä]', 'a', n)
    n = re.sub(r'[îï]', 'i', n)
    n = re.sub(r'[ôö]', 'o', n)
    n = re.sub(r'[ûùü]', 'u', n)
    n = re.sub(r'[ç]', 'c', n)
    return re.sub(r'[^a-z0-9._-]', '_', n)

# Initialisation
url = SUPABASE_URL if (SUPABASE_URL and SUPABASE_URL.endswith("/")) else f"{SUPABASE_URL}/"
supabase: Client = create_client(url, SUPABASE_KEY)
client_openai = OpenAI(api_key=OPENAI_API_KEY)

BUCKET_NAME = "daily-images"

def get_existing_words():
    """Récupère tous les mots déjà présents en base pour éviter les doublons."""
    try:
        response = supabase.table("daily_challenges").select("word").execute()
        return [item['word'].upper() for item in response.data]
    except Exception as e:
        print(f"⚠️ Impossible de récupérer les mots existants : {e}")
        return []

def get_validated_concept(existing_words):
    """Demande à GPT un concept et valide (longueur, accents, doublons)."""
    max_retries = 5
    for attempt in range(max_retries):
        print(f"🧠 Tentative d'idéation {attempt + 1}/{max_retries}...")
        try:
            response = client_openai.chat.completions.create(
                model="gpt-4o",
                response_format={ "type": "json_object" },
                messages=[
                    {"role": "system", "content": "Expert en énigmes visuelles pour Promptle."},
                    {"role": "user", "content": f"""
                        Génère un JSON :
                        - 'word_fr': UN NOM COMMUN EN FRANÇAIS (SANS ACCENTS, SANS ESPACES, 5-8 LETTRES).
                        - 'word_en': SA TRADUCTION EN ANGLAIS (5-8 LETTRES).
                        - 'image_prompt': un prompt pour DALL-E 3 (style macro, artistique, mystérieux).

                        LISTE NOIRE (NE PAS UTILISER CES MOTS) : {", ".join(existing_words[-50:])}
                    """}
                ]
            )
            concept = json.loads(response.choices[0].message.content)
            w_fr = concept.get('word_fr', '').upper()
            w_en = concept.get('word_en', '').upper()

            # Vérification validité + Vérification doublon
            if is_valid_word(w_fr) and is_valid_word(w_en):
                if w_fr not in existing_words:
                    return concept
                else:
                    print(f"⚠️ Doublon détecté : '{w_fr}' est déjà en base. Recommence...")
            else:
                print(f"⚠️ Mots invalides : {w_fr} / {w_en}")
        except Exception as e:
            print(f"❌ Erreur GPT : {e}")
    return None

def generate_challenge(target_date, existing_words):
    date_str = target_date.strftime('%Y-%m-%d')
    print(f"\n--- 🔮 Génération pour le {date_str} ---")

    concept = get_validated_concept(existing_words)
    if not concept: return

    word_fr, word_en = concept['word_fr'].upper(), concept['word_en'].upper()

    print(f"🎨 Création de l'image pour '{word_fr}'...")
    try:
        img_res = client_openai.images.generate(model="dall-e-3", prompt=concept['image_prompt'], n=1)
        img_url = img_res.data[0].url
    except Exception as e:
        print(f"❌ DALL-E : {e}"); return

    print("⚡ Optimisation & Upload...")
    try:
        img_data = requests.get(img_url).content
        img = Image.open(io.BytesIO(img_data))
        webp_buf = io.BytesIO()
        img.save(webp_buf, format="WEBP", quality=80)

        filename = sanitize_filename(f"{date_str}_{word_fr}.webp")
        supabase.storage.from_(BUCKET_NAME).upload(path=filename, file=webp_buf.getvalue(), file_options={"content-type": "image/webp"})
        public_url = supabase.storage.from_(BUCKET_NAME).get_public_url(filename)
    except Exception as e:
        print(f"❌ Storage : {e}"); return

    print("💾 Enregistrement DB...")
    try:
        supabase.table("daily_challenges").insert({
            "word": word_fr, "word_en": word_en, "image_url": public_url,
            "image_url_en": public_url, "publish_date": date_str, "hint": concept['image_prompt']
        }).execute()
        print(f"✨ Succès pour le {date_str} !")
        existing_words.append(word_fr) # On ajoute le mot à la liste locale
    except Exception as e:
        print(f"❌ DB : {e}")

def run_oracle():
    print("🚀 L'Oracle démarre sa ronde...")
    existing_words = get_existing_words()
    print(f"📊 {len(existing_words)} mots déjà en mémoire.")

    for i in range(0, 7):
        date_str = (datetime.now() + timedelta(days=i)).strftime('%Y-%m-%d')
        check = supabase.table("daily_challenges").select("id").eq("publish_date", date_str).execute()
        if not check.data:
            generate_challenge(datetime.now() + timedelta(days=i), existing_words)
        else:
            print(f"✅ {date_str} prêt.")

if __name__ == "__main__":
    run_oracle()
