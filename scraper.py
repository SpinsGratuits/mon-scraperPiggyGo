import json
import os
from datetime import datetime
import cloudscraper
from bs4 import BeautifulSoup

# --- CONFIGURATION ---
filename = "scrappiggygo.json"
sources = [
    "https://giveaway48.com/piggy-go-reward-links/",  # Source 1 : Corrigée sans le double 'h'
    "https://t.me/s/PiggyGoFreeRewards"               # Source 2 : Telegram Web public
]

# --- CHARGEMENT DE L'HISTORIQUE ---
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
        print(f"Impossible de lire l'historique : {e}")

# Client simulant un navigateur standard
scraper = cloudscraper.create_scraper(browser={'browser': 'chrome', 'platform': 'windows', 'mobile': False})

now = datetime.now()
date_now_str = now.strftime("%d/%m/%Y @ %H:%M")
date_du_jour_str = now.strftime("%d/%m/%Y")
heure_actuelle_str = now.strftime("%H:%M")

tous_les_liens_trouves = []

# --- PARCOURS DES SOURCES ---
for url in sources:
    print(f"Scraping de la source : {url}")
    try:
        response = scraper.get(url, timeout=15)
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, "html.parser")
            
            # Extraction de TOUS les liens HTML de la page
            links = soup.find_all("a", href=True)
            
            for link in links:
                href = link["href"]
                
                # FILTRE LARGE : On attrape les liens officiels de l'éditeur ou les redirections cadeaux
                # Valide les liens contenant f99, forevernine, piggygo ou les redirections externes de Giveaway
                if any(k in href.lower() for k in ["f99", "forevernine", "piggygo", "piggy-go"]):
                    # Éviter d'attraper les liens de partage vers Twitter/Facebook du site lui-même
                    if any(p in href.lower() for p in ["twitter.com", "facebook.com", "whatsapp"]):
                        continue
                        
                    tous_les_liens_trouves.append(href)
        else:
            print(f"-> Code d'erreur réseau : {response.status_code}")
    except Exception as e:
        print(f"-> Erreur sur cette source : {e}")

# Suppression des doublons de la session courante
tous_les_liens_trouves = list(set(tous_les_liens_trouves))
print(f"\nNombre total de liens uniques collectés : {len(tous_les_liens_trouves)}")

# --- PRÉPARATION DU JSON FLUTTERFLOW ---
json_data = []

for href in tous_les_liens_trouves:
    type_recompense = "Dés et Pièces"
    
    if href in anciens_liens:
        # Conserver l'ancien historique temporel exact pour vos utilisateurs
        json_data.append({
            "date_scraping": anciens_liens[href].get("date_scraping", date_now_str), 
            "date": anciens_liens[href].get("date", date_du_jour_str), 
            "heure": anciens_liens[href].get("heure", "00:00"),
            "recompense": anciens_liens[href].get("recompense", type_recompense), 
            "lienurl": href,
            "badge": "" 
        })
    else:
        # Nouveau lien détecté
        json_data.append({
            "date_scraping": date_now_str, 
            "date": date_du_jour_str, 
            "heure": heure_actuelle_str,
            "recompense": type_recompense, 
            "lienurl": href,
            "badge": "NEW" 
        })

# --- SAUVEGARDE ET SÉCURITÉ ---
if not json_data:
    if anciens_liens:
        print("Aucun lien détecté sur le web, conservation de vos anciens liens actuels.")
        json_data = list(anciens_liens.values())
    else:
        json_data.append({
            "date_scraping": date_now_str,
            "statut": "VIDE",
            "message": "Aucun lien extrait des sources distantes."
        })

with open(filename, mode="w", encoding="utf-8") as json_file:
    json.dump(json_data, json_file, indent=4, ensure_ascii=False)

print(f"Fichier {filename} mis à jour avec succès ({len(json_data)} éléments).")
