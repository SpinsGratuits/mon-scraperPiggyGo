import json
import os
from datetime import datetime
import cloudscraper
from bs4 import BeautifulSoup

# --- CONFIGURATION ---
filename = "scrappiggygo.json"
sources = [
    "https://giveaway48.com/piggy-go-reward-links/",
    "https://t.me/s/PiggyGoFreeRewards"
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
            links = soup.find_all("a", href=True)
            
            for link in links:
                href = link["href"].strip()
                
                # 1. SÉCURITÉ ABSOLUE : On rejette les liens internes Telegram et les liens relatifs du type /s/...
                if href.startswith("/") or "t.me" in href.lower() or "telegram.me" in href.lower():
                    continue
                
                # 2. SÉCURITÉ DES RÉSEAUX : On supprime les boutons de partage social
                if any(p in href.lower() for p in ["twitter.com", "facebook.com", "whatsapp", "pinterest"]):
                    continue
                
                # 3. FILTRE DES VRAIS LIENS CADEAUX : Doit être un lien complet externe
                # Les éditeurs de Piggy Go utilisent principalement f99.pro, forevernine ou des raccourcis comme t.co / bit.ly
                if any(k in href.lower() for k in ["f99", "forevernine", "piggygo", "piggy-go", "t.co", "bit.ly"]):
                    tous_les_liens_trouves.append(href)
                    
    except Exception as e:
        print(f"-> Erreur sur cette source : {e}")

# Suppression des doublons de session
tous_les_liens_trouves = list(set(tous_les_liens_trouves))
print(f"Nombre de vrais liens valides trouvés (hors Telegram) : {len(tous_les_liens_trouves)}")

# --- CONSTITUTION DU JSON POUR FLUTTERFLOW ---
json_data = []

for href in tous_les_liens_trouves:
    type_recompense = "Dés et Pièces"
    
    if href in anciens_liens:
        json_data.append({
            "date_scraping": anciens_liens[href].get("date_scraping", date_now_str), 
            "date": anciens_liens[href].get("date", date_du_jour_str), 
            "heure": anciens_liens[href].get("heure", "00:00"),
            "recompense": anciens_liens[href].get("recompense", type_recompense), 
            "lienurl": href,
            "badge": "" 
        })
    else:
        json_data.append({
            "date_scraping": date_now_str, 
            "date": date_du_jour_str, 
            "heure": heure_actuelle_str,
            "recompense": type_recompense, 
            "lienurl": href,
            "badge": "NEW" 
        })

if not json_data and anciens_liens:
    json_data = list(anciens_liens.values())

with open(filename, mode="w", encoding="utf-8") as json_file:
    json.dump(json_data, json_file, indent=4, ensure_ascii=False)

print(f"Fichier réécrit. Tous les liens polluants '/s/' ont été éradiqués.")
