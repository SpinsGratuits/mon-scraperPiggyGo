import json
import os
from datetime import datetime
import cloudscraper
from bs4 import BeautifulSoup

# --- 1. CONFIGURATION ---
# Changement de la source pour Mosttechs
url = "https://mosttechs.com/piggy-go-free-dice-links/"
filename = "scrappiggygo.json"

# --- 2. CHARGEMENT DE L'HISTORIQUE PRÉCÉDENT ---
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
        print(f"[Attention] Impossible de lire l'historique JSON : {e}")

# Client simulant un navigateur standard (contourne les protections Cloudflare de Mosttechs)
scraper = cloudscraper.create_scraper(browser={'browser': 'chrome', 'platform': 'windows', 'mobile': False})

try:
    response = scraper.get(url, timeout=15)
    status_code = response.status_code
    html_text = response.text
except Exception as e:
    status_code = 500
    html_text = ""
    print(f"[Erreur] Connexion au site impossible : {e}")

if status_code == 200:
    soup = BeautifulSoup(html_text, "html.parser")
    
    # Variables temporelles pour les nouveaux liens détectés
    now = datetime.now()
    date_now_str = now.strftime("%d/%m/%Y @ %H:%M")
    date_du_jour_str = now.strftime("%d/%m/%Y")
    heure_actuelle_str = now.strftime("%H:%M")
    
    tous_les_liens_trouves = []
    
    # 3. EXTRACTION ET FILTRAGE CHIRURGICAL DES LIENS
    all_links = soup.find_all("a", href=True)
    
    for link in all_links:
        href = link["href"].strip()
        
        # RÈGLE A : Supprimer les liens de navigation interne (ex: /s/...) ou les redirections Telegram
        if href.startswith("/") or "t.me" in href.lower() or "telegram.me" in href.lower():
            continue
            
        # RÈGLE B : Supprimer les boutons de partage social du site (Twitter, Facebook, Pinterest...)
        if any(p in href.lower() for p in ["twitter.com", "facebook.com", "whatsapp", "pinterest", "reddit.com"]):
            continue
            
        # RÈGLE C : Isoler uniquement les vrais domaines cadeaux de Piggy Go et raccourcisseurs
        # (L'éditeur utilise f99.pro, forevernine, ou des réducteurs de liens courts de redirection)
        keywords = ["f99", "forevernine", "piggygo", "piggy-go", "t.co", "bit.ly"]
        if any(key in href.lower() for key in keywords):
            tous_les_liens_trouves.append(href)

    # Suppression des doublons stricts au sein de cette session de crawl
    tous_les_liens_trouves = list(set(tous_les_liens_trouves))
    print(f"[Succès] {len(tous_les_liens_trouves)} vrais liens cadeaux isolés depuis Mosttechs.")

    # --- 4. STRUCTURATION DU JSON FLUTTERFLOW ---
    json_data = []
    
    for href in tous_les_liens_trouves:
        type_recompense = "Dés et Pièces"
        
        if href in anciens_liens:
            # Lien connu : on garde ses données temporelles d'origine pour éviter les sauts de date
            json_data.append({
                "date_scraping": anciens_liens[href].get("date_scraping", date_now_str), 
                "date": anciens_liens[href].get("date", date_du_jour_str), 
                "heure": anciens_liens[href].get("heure", "00:00"),
                "recompense": anciens_liens[href].get("recompense", type_recompense), 
                "lienurl": href,
                "badge": "" 
            })
        else:
            # Nouveau lien fraîchement publié sur le site
            json_data.append({
                "date_scraping": date_now_str, 
                "date": date_du_jour_str, 
                "heure": heure_actuelle_str,
                "recompense": type_recompense, 
                "lienurl": href,
                "badge": "NEW" 
            })

    # File-safe : Si le site renvoie 0 liens par erreur, on préserve l'ancienne base pour l'application
    if not json_data and anciens_liens:
        print("[Alerte] Aucun lien trouvé lors du crawl, préservation de l'historique existant.")
        json_data = list(anciens_liens.values())

    # --- 5. ENREGISTREMENT ---
    with open(filename, mode="w", encoding="utf-8") as json_file:
        json.dump(json_data, json_file, indent=4, ensure_ascii=False)
        
    print(f"[Terminé] Le fichier {filename} a été mis à jour avec succès ({len(json_data)} éléments).")
            
else:
    print(f"[Erreur] Échec d'accès réseau (Code {status_code}). Mosttechs bloque peut-être la requête.")
