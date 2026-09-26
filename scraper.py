import json
import os
import re
from datetime import datetime
import cloudscraper
from bs4 import BeautifulSoup

# 1. URL du site cible et nom de votre fichier JSON
url = "https://www.topactualites.com/piggy-go-des-et-pieces-gratuits-liens-quotidiens/"
filename = "scrappiggygo.json"

# --- CHARGEMENT DE L'HISTORIQUE PRÉCÉDENT ---
# Dictionnaire indexé par l'URL pour retrouver instantanément les données déjà scrapées
anciens_liens = {}
if os.path.exists(filename):
    try:
        with open(filename, mode="r", encoding="utf-8") as json_file:
            data_chargee = json.load(json_file)
            # On s'assure que c'est une liste valide
            if isinstance(data_chargee, list):
                for item in data_chargee:
                    if "lienurl" in item:
                        anciens_liens[item["lienurl"]] = item
    except Exception as e:
        print(f"Impossible de lire le fichier JSON précédent (il sera recréé) : {e}")

# Création d'un scraper imitant un navigateur Chrome sur Windows
scraper = cloudscraper.create_scraper(browser={'browser': 'chrome', 'platform': 'windows', 'mobile': False})

try:
    response = scraper.get(url, timeout=15)
    status_code = response.status_code
    html_text = response.text
except Exception as e:
    status_code = 500
    html_text = ""
    print(f"Erreur lors du contournement du blocage : {e}")

if status_code == 200:
    soup = BeautifulSoup(html_text, "html.parser")
    
    # Variables temporelles de votre machine pour les NOUVEAUX liens uniquement
    now = datetime.now()
    date_now_str = now.strftime("%d/%m/%Y @ %H:%M")
    date_du_jour_str = now.strftime("%d/%m/%Y")
    heure_actuelle_str = now.strftime("%H:%M")
    
    # Liste finale qui sera réécrite dans le JSON
    json_data = []
    
    # 2. Scanner TOUS les liens hypertextes de la page
    all_links = soup.find_all("a", href=True)
    
    for link in all_links:
        href = link["href"].strip()
        texte_lien = link.get_text(strip=True)
        
        # SÉCURITÉ : Ignorer les liens cassés ou internes de navigation relative /s/
        if href.startswith("/") or "t.me" in href.lower() or "telegram.me" in href.lower():
            continue
            
        # Filtre strict : sur ce site, les liens de récompenses portent le texte exact "Collectez"
        if texte_lien.lower() == "collectez":
            
            # Éviter les doublons stricts au sein d'une même session de scraping
            if any(item["lienurl"] == href for item in json_data):
                continue
                
            # --- EXTRACTION DE LA RÉCOMPENSE ---
            # On remonte au parent pour attraper le contexte de la récompense (ex: "Jetons gratuit")
            parent = link.find_parent()
            parent_text = parent.get_text(separator=" ").strip() if parent else ""
            if len(parent_text) < 15 and parent and parent.find_parent():
                parent_text = parent.find_parent().get_text(separator=" ").strip()
            
            clean_text = " ".join(parent_text.split())
            
            # Capture des mentions (jetons, dés, pièces, etc.) placées juste au-dessus du bouton
            recompense_match = re.search(r'(?:jetons|dés|des|pieces|pièces|coins|spins|tours)\s*\w*', clean_text, re.IGNORECASE)
            type_recompense = recompense_match.group(0).strip() if recompense_match else "Jetons gratuit"
            
            # Capitalisation propre pour votre affichage (ex: "Jetons gratuit")
            type_recompense = type_recompense.capitalize()
            
            # --- LOGIQUE DE DOUBLE-VÉRIFICATION ET CONSERVATION ---
            if href in anciens_liens:
                # DOUBLON DÉTECTÉ : On conserve EXACTEMENT toutes les anciennes valeurs temporelles
                json_data.append({
                    "date_scraping": anciens_liens[href].get("date_scraping", date_now_str), 
                    "date": anciens_liens[href].get("date", date_du_jour_str), 
                    "heure": anciens_liens[href].get("heure", "00:00"),
                    "recompense": type_recompense, 
                    "lienurl": href,
                    "badge": ""  # Ancien lien, aucun texte additionnel
                })
            else:
                # NOUVEAU LIEN : On applique la date et l'heure de l'exécution actuelle
                json_data.append({
                    "date_scraping": date_now_str, 
                    "date": date_du_jour_str, 
                    "heure": heure_actuelle_str,
                    "recompense": type_recompense, 
                    "lienurl": href,
                    "badge": "NEW"  # Texte "NEW" pour l'affichage FlutterFlow
                })

    # 3. Écriture du fichier JSON mis à jour
    if not json_data:
        # En cas de page vide ou indisponible, on préserve l'historique plutôt que de tout effacer
        if anciens_liens:
            print("Aucun lien extrait, conservation de l'historique précédent.")
            json_data = list(anciens_liens.values())
        else:
            json_data.append({
                "date_scraping": date_now_str,
                "statut": "VIDE",
                "message": "Aucun lien trouvé sur la page. Vérifiez manuellement le site."
            })
            print("Aucun lien extrait de la source.")
    else:
        print(f"Succès total ! {len(json_data)} liens traités (Anciens préservés + Nouveaux ajoutés).")

    with open(filename, mode="w", encoding="utf-8") as json_file:
        json.dump(json_data, json_file, indent=4, ensure_ascii=False)
            
else:
    print(f"Erreur d'accès réseau (Code {status_code}). Le site bloque toujours.")
