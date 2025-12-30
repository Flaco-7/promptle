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
env_path = os.path.join(os.path.dirname(__file__), '.env')
load_dotenv(dotenv_path=env_path)

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
    # Supprime les accents manuellement au cas où
    n = filename.lower()
    n = re.sub(r'[éèêë]', 'e', n)
    n = re.sub(r'[àâä]', 'a', n)
    n = re.sub(r'[îï]', 'i', n)
    n = re.sub(r'[ôö]', 'o', n)
    n = re.sub(r'[ûùü]', 'u', n)
    n = re.sub(r'[ç]', 'c', n)
    # Ne garde que l'essentiel
    return re.sub(r'[^a-z0-9._-]', '_', n)

def check_env_vars():
    if not SUPABASE_URL or "supabase.co" not in SUPABASE_URL:
        print(f"❌ URL Supabase invalide : {SUPABASE_URL}")
        sys.exit(1)
    if not SUPABASE_KEY:
        print("❌ Clé SERVICE_ROLE manquante.")
        sys.exit(1)
    print(f"✅ Configuration chargée pour : {SUPABASE_URL}")

check_env_vars()

try:
    client_openai = OpenAI(api_key=OPENAI_API_KEY)
    # S'assurer que l'URL se termine par / pour éviter le warning
    url = SUPABASE_URL if SUPABASE_URL.endswith("/") else f"{SUPABASE_URL}/"
    supabase: Client = create_client(url, SUPABASE_KEY)
except Exception as e:
    print(f"❌ Erreur initialisation : {e}")
    sys.exit(1)

BUCKET_NAME = "daily-images"

def get_validated_concept():
    """Demande à GPT un concept et recommence tant qu'il n'est pas valide."""
    max_retries = 5
    for attempt in range(max_retries):
        print(f"🧠 Tentative d'idéation {attempt + 1}/{max_retries}...")
        try:
            response = client_openai.chat.completions.create(
                model="gpt-4o",
                response_format={ "type": "json_object" },
                messages=[
                    {"role": "system", "content": "Tu es un expert en énigmes pour le jeu Promptle."},
                    {"role": "user", "content": """
                        Génère un objet JSON :
                        - 'word_fr': UN NOM COMMUN EN FRANÇAIS (SANS ACCENTS, SANS ESPACES).
                        - 'word_en': SA TRADUCTION EN ANGLAIS.
                        - 'image_prompt': un prompt pour DALL-E 3 (style macro, mystérieux).

                        CONTRAINTES STRICTES :
                        1. Les deux mots DOIVENT faire entre 5 et 8 lettres.
                        2. AUCUN ACCENT, AUCUNE CÉDILLE (ex: utiliser FOUGERE et non FOUGÈRE).
                        3. Les deux mots doivent être différents de 'PROMPT'.
                    """}
                ]
            )
            concept = json.loads(response.choices[0].message.content)
            word_fr = concept.get('word_fr', '').upper()
            word_en = concept.get('word_en', '').upper()

            if is_valid_word(word_fr) and is_valid_word(word_en):
                print(f"✅ Concept validé : {word_fr} ({len(word_fr)} l.) / {word_en} ({len(word_en)} l.)")
                return concept
            else:
                print(f"⚠️ Mots invalides reçus : {word_fr} / {word_en}. Nouvelle tentative...")
        except Exception as e:
            print(f"❌ Erreur lors de l'appel GPT : {e}")

    return None

def generate_challenge(target_date):
    date_str = target_date.strftime('%Y-%m-%d')
    print(f"\n--- 🔮 Génération pour le {date_str} ---")

    concept = get_validated_concept()
    if not concept:
        print("❌ Impossible d'obtenir un concept valide après plusieurs tentatives.")
        return

    word_fr = concept['word_fr'].upper()
    word_en = concept['word_en'].upper()

    print("🎨 Création de l'image (DALL-E 3)...")
    try:
        img_res = client_openai.images.generate(
            model="dall-e-3",
            prompt=concept['image_prompt'],
            size="1024x1024",
            quality="standard",
            n=1
        )
        img_url = img_res.data[0].url
    except Exception as e:
        print(f"❌ Erreur DALL-E : {e}")
        return

    print("⚡ Optimisation et Upload...")
    try:
        img_data = requests.get(img_url).content
        img = Image.open(io.BytesIO(img_data))
        webp_buf = io.BytesIO()
        img.save(webp_buf, format="WEBP", quality=80)

        filename = sanitize_filename(f"{date_str}_{word_fr}.webp")
        print(f"📦 Upload {filename}...")

        supabase.storage.from_(BUCKET_NAME).upload(
            path=filename,
            file=webp_buf.getvalue(),
            file_options={"content-type": "image/webp"}
        )
        public_url = supabase.storage.from_(BUCKET_NAME).get_public_url(filename)
    except Exception as e:
        print(f"❌ Erreur Storage : {e}")
        return

    print("💾 Enregistrement DB...")
    try:
        supabase.table("daily_challenges").insert({
            "word": word_fr,
            "word_en": word_en,
            "image_url": public_url,
            "image_url_en": public_url,
            "publish_date": date_str,
            "hint": concept['image_prompt']
        }).execute()
        print(f"✨ Succès total pour le {date_str} !")
    except Exception as e:
        print(f"❌ Erreur DB : {e}")

def run_oracle():
    print("🚀 L'Oracle démarre sa ronde...")
    for i in range(0, 7):
        date_str = (datetime.now() + timedelta(days=i)).strftime('%Y-%m-%d')
        try:
            check = supabase.table("daily_challenges").select("id").eq("publish_date", date_str).execute()
            if not check.data:
                generate_challenge(datetime.now() + timedelta(days=i))
            else:
                print(f"✅ {date_str} est déjà prêt.")
        except Exception as e:
            print(f"❌ Erreur connexion Supabase : {e}")
            break

if __name__ == "__main__":
    run_oracle()
