import json
import os
from datetime import datetime, timedelta
import cloudscraper
from bs4 import BeautifulSoup

# --- 1. CONFIGURATION ---
url = "https://mosttechs.com/piggy-go-free-dice-links/"
filename = "scrappiggygo.json"

# --- 2. CHARGEMENT ET NETTOYAGE DE L'HISTORIQUE ---
anciens_liens = {}
now = datetime.now()

# Seuil d'expiration modifié à 6 jours (144 heures)
limite_validite = now - timedelta(days=6)

if os.path.exists(filename):
    try:
        with open(filename, mode="r", encoding="utf-8") as json_file:
            data_chargee = json.load(json_file)
            if isinstance(data_chargee, list):
                for item in data_chargee:
                    if "lienurl" in item:
                        # Nettoyage automatique : on ignore les liens de plus de 6 jours
                        try:
                            date_scrap = datetime.strptime(item.get("date_scraping", ""), "%d/%m/%Y @ %H:%M")
                            if date_scrap < limite_validite:
                                continue  # Trop vieux (plus de 6 jours), on supprime
                        except:
                            pass
                        
                        anciens_liens[item["lienurl"]] = item
        print(f"[Info] {len(anciens_liens)} anciens liens valides (de moins de 6 jours) conservés.")
    except Exception as e:
        print(f"[Attention] Impossible de lire l'historique JSON : {e}")

# Variables temporelles pour les nouveaux liens détectés
date_now_str = now.strftime("%d/%m/%Y @ %H:%M")
date_du_jour_str = now.strftime("%d/%m/%Y")
heure_actuelle_str = now.strftime("%H:%M")

# Client anti-bot pour contourner Cloudflare
scraper = cloudscraper.create_scraper(browser={'browser': 'chrome', 'platform': 'windows', 'mobile': False})

try:
    response = scraper.get(url, timeout=15)
    status_code = response.status_code
    html_text = response.text
except Exception as e:
    status_code = 500
    html_text = ""
    print(f"[Erreur] Connexion impossible : {e}")

if status_code == 200:
    soup = BeautifulSoup(html_text, "html.parser")
    tous_les_liens_trouves = []
    
    # 3. EXTRACTION ET FILTRAGE DES LIENS SORTANTS
    all_links = soup.find_all("a", href=True)
    
    for link in all_links:
        href = link["href"].strip()
        
        # Filtres de sécurité (Telegram, réseaux sociaux, liens relatifs)
        if href.startswith("/") or "t.me" in href.lower() or "telegram.me" in href.lower():
            continue
        if any(p in href.lower() for p in ["twitter.com", "facebook.com", "whatsapp", "pinterest", "reddit.com"]):
            continue
            
        # Isoler uniquement les liens officiels de récompenses Piggy Go
        keywords = ["f99", "forevernine", "piggygo", "piggy-go", "t.co", "bit.ly"]
        if any(key in href.lower() for key in keywords):
            tous_les_liens_trouves.append(href)

    # Dédoublonnage de la session courante
    tous_les_liens_trouves = list(set(tous_les_liens_trouves))

    # --- 4. STRUCTURATION DU RESTE DE LA LISTE ---
    json_data = []
    
    for href in tous_les_liens_trouves:
        type_recompense = "Dés et Pièces"
        
        if href in anciens_liens:
            # Lien existant : on conserve ses données d'époque (pour ne pas casser le tri)
            json_data.append({
                "date_scraping": anciens_liens[href].get("date_scraping", date_now_str), 
                "date": anciens_liens[href].get("date", date_du_jour_str), 
                "heure": anciens_liens[href].get("heure", "00:00"),
                "recompense": anciens_liens[href].get("recompense", type_recompense), 
                "lienurl": href,
                "badge": "" 
            })
        else:
            # Nouveau lien : on lui applique la date de cette exécution
            json_data.append({
                "date_scraping": date_now_str, 
                "date": date_du_jour_str, 
                "heure": heure_actuelle_str,
                "recompense": type_recompense, 
                "lienurl": href,
                "badge": "NEW" 
            })

    # Si le site est inaccessible ou ne renvoie rien, on sauvegarde au moins l'historique nettoyé
    if not json_data and anciens_liens:
        json_data = list(anciens_liens.values())

    # --- 5. TRI CHRONOLOGIQUE STRICT (Le dernier paru en haut de la liste) ---
    def extraire_date_tri(item):
        try:
            return datetime.strptime(item.get("date_scraping", ""), "%d/%m/%Y @ %H:%M")
        except:
            return datetime.min

    # Tri décroissant basé sur la date de découverte
    json_data.sort(key=extraire_date_tri, reverse=True)

    # --- 6. SAUVEGARDE ET ENREGISTREMENT ---
    with open(filename, mode="w", encoding="utf-8") as json_file:
        json.dump(json_data, json_file, indent=4, ensure_ascii=False)
        
    print(f"[Terminé] Fichier mis à jour. Nombre de liens optimisés : {len(json_data)} (Historique de 6 jours maximum, classé du plus récent au plus ancien).")
            
else:
    print(f"[Erreur] Échec réseau (Code {status_code}).")
