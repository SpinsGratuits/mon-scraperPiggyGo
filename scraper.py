import json
import os
import re
from datetime import datetime, timedelta
import cloudscraper
from bs4 import BeautifulSoup

# --- 1. CONFIGURATION ---
url = "https://mosttechs.com/piggy-go-free-dice-links/"
filename = "scrappiggygo.json"

# Dictionnaire de traduction des mois pour faciliter la conversion en vraies dates Python
mois_en_to_num = {
    "january": "01", "januray": "01", "february": "02", "february ": "02", "march": "03", 
    "april": "04", "may": "05", "june": "06", "july": "07", "august": "08", 
    "september": "09", "october": "10", "november": "11", "december": "12"
}

# --- 2. CHARGEMENT DE L'HISTORIQUE ---
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

# Client de contournement Cloudflare
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
    
    now = datetime.now()
    date_now_str = now.strftime("%d/%m/%Y @ %H:%M")
    heure_actuelle_str = now.strftime("%H:%M")
    
    # Seuil limite : on supprime du fichier ce qui est vieux de plus de 6 jours par rapport à aujourd'hui
    limite_conservation = now - timedelta(days=6)
    
    json_data = []
    
    # Trouver l'élément conteneur principal de l'article pour éviter les menus
    entry_content = soup.find(class_="entry-content")
    if not entry_content:
        entry_content = soup  # Sécurité de secours
        
    # 3. PARCOURS CHRONOLOGIQUE DES BLOCS DE TEXTE
    current_date_str = now.strftime("%d/%m/%Y")  # Date par défaut au cas où
    
    # On examine tous les enfants du contenu textuel pour repérer les dates et les liens associés juste après
    for element in entry_content.find_all(["p", "ul", "ol", "strong"]):
        text = element.get_text().strip().lower()
        
        # Détection d'une ligne de date (Ex: "26 september 2026")
        match_date = re.search(r'(\d{1,2})\s+([a-z]+)\s+(\d{4})', text)
        if match_date:
            jour = match_date.group(1).zfill(2)
            nom_mois = match_date.group(2)
            annee = match_date.group(3)
            
            # Conversion du mois écrit en chiffres exploitables
            num_mois = mois_en_to_num.get(nom_mois, "01")
            current_date_str = f"{jour}/{num_mois}/{annee}"
            continue  # Passer à l'élément suivant pour chercher les liens sous cette date
            
        # Si cet élément contient un ou plusieurs liens hypertextes
        links = element.find_all("a", href=True)
        for link in links:
            href = link["href"].strip()
            
            # Filtres de nettoyage chirurgicaux (Réseaux sociaux, Telegram, liens relatifs)
            if href.startswith("/") or "t.me" in href.lower() or "telegram.me" in href.lower():
                continue
            if any(p in href.lower() for p in ["twitter.com", "facebook.com", "whatsapp", "pinterest", "reddit.com"]):
                continue
                
            # Validation du domaine officiel de récompense du jeu
            keywords = ["f99", "forevernine", "piggygo", "piggy-go", "t.co", "bit.ly"]
            if any(key in href.lower() for key in keywords):
                
                # Vérification de la limite des 6 jours pour cette récompense par rapport à aujourd'hui
                try:
                    date_objet = datetime.strptime(current_date_str, "%d/%m/%Y")
                    if date_objet < limite_conservation:
                        continue  # Lien de plus de 6 jours ignoré
                except:
                    pass
                
                # Éviter les doublons stricts lors de la session de lecture
                if any(item["lienurl"] == href for item in json_data):
                    continue
                
                type_recompense = "Dés et Pièces"
                
                # Construction de la nouvelle donnée combinée (Date Parution + Heure du Scraping)
                date_scraping1_combinee = f"{current_date_str} @ {heure_actuelle_str}"
                
                # --- STRATÉGIE DE RECONSTITUTION ---
                if href in anciens_liens:
                    # Lien existant : On garde son historique mais on met à jour la parution et date_scraping1
                    json_data.append({
                        "date_scraping": anciens_liens[href].get("date_scraping", date_now_str), 
                        "date_scraping1": anciens_liens[href].get("date_scraping1", date_scraping1_combinee),
                        "date": current_date_str,  
                        "heure": anciens_liens[href].get("heure", "00:00"),
                        "recompense": anciens_liens[href].get("recompense", type_recompense), 
                        "lienurl": href,
                        "badge": "" 
                    })
                else:
                    # Nouveau lien paru sur le site
                    json_data.append({
                        "date_scraping": date_now_str, 
                        "date_scraping1": date_scraping1_combinee,
                        "date": current_date_str,  
                        "heure": heure_actuelle_str,
                        "recompense": type_recompense, 
                        "lienurl": href,
                        "badge": "NEW" 
                    })

    # Si le site est momentanément en panne, on préserve l'ancienne base saine
    if not json_data and anciens_liens:
        json_data = list(anciens_liens.values())

    # --- 4. TRI ALGORITHMIQUE PAR LA DATE DE PARUTION DU SITE (Du plus récent au plus ancien) ---
    def extraire_cle_parution(item):
        try:
            date_part = datetime.strptime(item.get("date", ""), "%d/%m/%Y")
            return date_part.timestamp()
        except:
            return 0

    # Tri descendant : Les dates de parutions les plus récentes se retrouvent en haut (index 0)
    json_data.sort(key=extraire_cle_parution, reverse=True)

    # --- 5. SAUVEGARDE DU FICHIER JSON ---
    with open(filename, mode="w", encoding="utf-8") as json_file:
        json.dump(json_data, json_file, indent=4, ensure_ascii=False)
        
    print(f"[Terminé] Fichier mis à jour avec succès : {len(json_data)} liens classés chronologiquement. Donnée 'date_scraping1' intégrée.")
            
else:
    print(f"[Erreur] Échec d'accès réseau (Code {status_code}).")
