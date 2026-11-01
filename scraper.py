import requests
from bs4 import BeautifulSoup
from datetime import datetime
from supabase import create_client, Client
from urllib.parse import urljoin
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# 1. Configurazione Supabase
SUPABASE_URL = "https://vdskoxutlhsdksbsplqp.supabase.co"
SUPABASE_KEY = "sb_publishable_ENqtzU8uti18iFwlxF4IXQ_WgQ7cbOg" 
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# 2. Funzione di Scraping
def estrai_bandi(nome_comune, url_bandi):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Cerco nuovi bandi per {nome_comune}...")
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
    
    try:
        response = requests.get(url_bandi, headers=headers, verify=False)
        response.raise_for_status() 
        
        soup = BeautifulSoup(response.text, 'html.parser')
        bandi_trovati = []
        
        # LOGICA SPECIFICA PER SPOLTORE (Tabella)
        # LOGICA SPECIFICA PER SPOLTORE (Tabella)
        if nome_comune == "Spoltore":
            righe = soup.find_all('tr')
            for riga in righe[1:]: # Salta la riga di intestazione
                colonne = riga.find_all('td')
                if len(colonne) >= 4:
                    titolo = colonne[3].get_text(strip=True)
                    link_tag = riga.find('a')
                    
                    if link_tag and 'href' in link_tag.attrs:
                        link_bando = "https://albo.tinnvision.cloud/" + link_tag['href']
                    else:
                        # Crea un link unico usando il numero di pubblicazione della prima colonna
                        id_pubb = colonne[0].get_text(strip=True).replace(' ', '').replace('/', '-')
                        link_bando = f"{url_bandi}&doc={id_pubb}"
                        
                    data = datetime.today().strftime('%d/%m/%Y')
                    
                    if titolo:
                        bandi_trovati.append({
                            "comune": nome_comune, 
                            "titolo": titolo,
                            "data_scadenza": data,
                            "link": link_bando
                        })
                        
        # LOGICA UNIVERSALE PER MONTESILVANO E PESCARA (Card)
        else:
            elementi_bando = soup.find_all('div', class_=lambda c: c and 'card' in c) 
            
            for elemento in elementi_bando:
                titolo_tag = elemento.find('h3', class_='card-title')
                
                if titolo_tag:
                    titolo = titolo_tag.text.strip()
                    tutti_i_link = elemento.find_all('a', href=True)
                    
                    if tutti_i_link:
                        link_tag = max(tutti_i_link, key=lambda tag: len(tag['href']))
                        link_grezzo = link_tag['href']
                        data = datetime.today().strftime('%d/%m/%Y')
                        link_assoluto = urljoin(url_bandi, link_grezzo)
                            
                        bandi_trovati.append({
                            "comune": nome_comune,
                            "titolo": titolo,
                            "data_scadenza": data,
                            "link": link_assoluto
                        })
                    
        return bandi_trovati
        
    except Exception as e:
        print(f"Errore di connessione per {nome_comune}: {e}")
        return []

# 3. Salvataggio su Supabase
def salva_bandi_supabase(bandi, nome_comune):
    if not bandi:
        return
        
    nuovi_inserimenti = 0
    for bando in bandi:
        risultato = supabase.table('bandi').select('id').eq('link', bando['link']).execute()
        
        if not risultato.data:
            supabase.table('bandi').insert(bando).execute()
            nuovi_inserimenti += 1
            
    print(f"-> {nome_comune}: Salvati {nuovi_inserimenti} nuovi bandi (su {len(bandi)} analizzati).")


# --- MOTORE DI ESECUZIONE MULTIPLA ---
if __name__ == "__main__":
    
    comuni_da_monitorare = [
        {
            "nome": "Montesilvano",
            "url": "https://www.comune.montesilvano.pe.it/Novita/Avvisi"
        },
        {
            "nome": "Pescara",
            "url": "https://comune.pescara.it/tipi_notizia/avvisi/"
        },
        {   
            "nome": "Spoltore",
            "url": "https://albo.tinnvision.cloud/?ente=00128340684"
        }
    ]
    
    print("Avvio scansione massiva...")
    print("-" * 50)
    
    for comune in comuni_da_monitorare:
        dati_estratti = estrai_bandi(comune["nome"], comune["url"])
        salva_bandi_supabase(dati_estratti, comune["nome"])
        print("-" * 50)
        
    print("Scansione completata!")
