import json
import os
import re
from datetime import datetime
import cloudscraper

# --- CONFIGURATION DES SOURCES ET FICHIER ---
filename = "scrappiggygo.json"
sources = [
    "https://giveaway48.com/piggy-go-reward-links/", # Source 1 : Blog US mis à jour mondialement
    "https://t.me"              # Source 2 : Telegram (Version Web publique)
]

# Pattern Regex robuste pour attraper toutes les URLs officielles de cadeaux Piggy Go
# (Filtre les domaines de l'éditeur comme f99.pro, forevernine.com ou piggygo-jy)
pattern_lien_officiel = r'https://[a-zA-Z0-9-._]+\.(?:forevernine|f99)\.com/[^\s"\']+'

# --- CHARGEMENT DE L'HISTORIQUE DE VOTRE APP ---
anciens_liens = {}
if os.path.exists(filename):
    try:
        with open(filename, mode="r", encoding="utf-8") as json_file:
            data_chargee = json.load(json_file)
            if isinstance(data_chargee, list):
                for item in data_chargee:
                    if "lienurl" in item:
                        anciens_liens[item["lienurl"]] = item
    except Exception as e:
        print(f"Impossible de lire le fichier JSON précédent : {e}")

# Création du client simulant un vrai navigateur
scraper = cloudscraper.create_scraper(browser={'browser': 'chrome', 'platform': 'windows', 'mobile': False})

# Variables temporelles pour les nouveaux éléments
now = datetime.now()
date_now_str = now.strftime("%d/%m/%Y @ %H:%M")
date_du_jour_str = now.strftime("%d/%m/%Y")
heure_actuelle_str = now.strftime("%H:%M")

# Liste de session pour fusionner sans doublon
tous_les_liens_trouves = []

# --- DU SCRAPING MULTI-SOURCES ---
for url in sources:
    print(f"Extraction en cours sur : {url} ...")
    try:
        response = scraper.get(url, timeout=15)
        if response.status_code == 200:
            # Extraction directe par Regex dans le code HTML brut aspired
            liens_source = re.findall(pattern_lien_officiel, response.text)
            print(f"-> {len(liens_source)} liens potentiels identifiés.")
            tous_les_liens_trouves.extend(liens_source)
        else:
            print(f"-> Échec d'accès (Code {response.status_code})")
    except Exception as e:
        print(f"-> Erreur lors du scraping de cette source : {e}")

# Nettoyage des doublons stricts trouvés pendant cette session
tous_les_liens_trouves = list(set(tous_les_liens_trouves))

# --- RECONSTITUTION ET STRATÉGIE FLUTTERFLOW ---
json_data = []

for href in tous_les_liens_trouves:
    # Éviter un doublon résiduel dans la liste finale
    if any(item["lienurl"] == href for item in json_data):
        continue
        
    type_recompense = "Dés et Pièces"
    
    # Si le lien existait déjà dans votre fichier JSON
    if href in anciens_liens:
        json_data.append({
            "date_scraping": anciens_liens[href].get("date_scraping", date_now_str), 
            "date": anciens_liens[href].get("date", date_du_jour_str), 
            "heure": anciens_liens[href].get("heure", "00:00"),
            "recompense": anciens_liens[href].get("recompense", type_recompense), 
            "lienurl": href,
            "badge": "" # Plus de badge pour les anciens liens
        })
    else:
        # C'est un tout nouveau lien fraîchement sorti sur le web !
        json_data.append({
            "date_scraping": date_now_str, 
            "date": date_du_jour_str, 
            "heure": heure_actuelle_str,
            "recompense": type_recompense, 
            "lienurl": href,
            "badge": "NEW" # Badge visible pour vos utilisateurs
        })

# --- ENREGISTREMENT SÉCURISÉ ---
if not json_data:
    # Sauvegarde de secours si les deux sites tombent en même temps
    if anciens_liens:
        print("Aucun lien frais trouvé, conservation de l'historique existant.")
        json_data = list(anciens_liens.values())
    else:
        json_data.append({
            "date_scraping": date_now_str,
            "statut": "VIDE",
            "message": "Aucun lien extrait des deux sources."
        })

print(f"\nTraitement terminé : {len(json_data)} liens enregistrés dans {filename}.")

with open(filename, mode="w", encoding="utf-8") as json_file:
    json.dump(json_data, json_file, indent=4, ensure_ascii=False)
