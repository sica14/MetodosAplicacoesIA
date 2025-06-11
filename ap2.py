import time
import requests
import subprocess
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import ollama

# =========================
# CONFIGURAÇÕES
# =========================
CHROME_PATH = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
USER_DATA_DIR = r"C:\bot-chrome-profile"
LIMITE_ITENS = 10
INTERVALO_VERIFICACAO = 60
NOME_MODELO_OLLAMA = "mistral:latest"

# =========================
# FUNÇÕES
# =========================

def construir_url_colecao(slug):
    return f"https://magiceden.io/ordinals/marketplace/{slug}"

def iniciar_chrome_com_debug():
    comando = f'"{CHROME_PATH}" --remote-debugging-port=9222 --user-data-dir="{USER_DATA_DIR}"'
    subprocess.Popen(comando, shell=True)
    print(f"[🧪] Chrome iniciado com perfil: {USER_DATA_DIR}")

def iniciar_navegador():
    options = Options()
    options.add_experimental_option("debuggerAddress", "127.0.0.1:9222")
    return webdriver.Chrome(options=options)

def obter_precos_dos_cards(driver):
    try:
        cards = WebDriverWait(driver, 10).until(
            EC.presence_of_all_elements_located((By.CSS_SELECTOR, "div[role='button'].flex.flex-col"))
        )
        precos = []
        for i, card in enumerate(cards[:LIMITE_ITENS]):
            try:
                preco_elem = card.find_element(By.CSS_SELECTOR, "div.font-semibold > span.text")
                preco = float(preco_elem.text.strip())
                precos.append(preco)
            except Exception:
                pass
        return precos
    except:
        return []

def obter_preco_btc_usd():
    try:
        r = requests.get("https://api.coingecko.com/api/v3/simple/price?ids=bitcoin&vs_currencies=usd")
        return r.json()["bitcoin"]["usd"]
    except Exception as e:
        print(f"⚠️ Erro ao obter preço do BTC: {e}")
        return None

def sugerir_preco_ia(precos_btc, preco_btc_usd):
    prompt = (
        f"Você é uma IA especialista em negociação de NFTs. Com base nesses preços em BTC: {precos_btc} "
        f"e sabendo que 1 BTC vale {preco_btc_usd} dólares, diga um preço ideal (em BTC) para ofertar "
        f"levemente abaixo do menor valor listado, visando lucro. Retorne apenas o número, sem explicações."
    )
    try:
        resposta = ollama.chat(
            model=NOME_MODELO_OLLAMA,
            messages=[{"role": "user", "content": prompt}]
        )
        texto = resposta['message']['content']
        sugestao = float(texto.strip().replace(",", "."))
        return sugestao
    except Exception as e:
        print(f"⚠️ IA falhou em gerar sugestão válida: {e}")
        return None

def enviar_oferta(driver, valor_btc):
    try:
        input_preco = WebDriverWait(driver, 6).until(
            EC.presence_of_element_located((By.ID, "collection-offer-price"))
        )
        input_preco.click()
        input_preco.send_keys(Keys.CONTROL, 'a')
        input_preco.send_keys(str(valor_btc))
        time.sleep(1)

        botao_submit = WebDriverWait(driver, 6).until(
            EC.element_to_be_clickable((By.XPATH, "//button[contains(., 'Submit Item Offer')]"))
        )
        botao_submit.click()
        print(f"✅ Oferta enviada: {valor_btc} BTC")
        time.sleep(2)
    except Exception as e:
        print(f"❌ Erro ao enviar oferta: {e}")

# =========================
# LOOP PRINCIPAL
# =========================

def executar_bot():
    print("🤖 IA de ofertas Magic Eden (com Coingecko).")
    slug = input("👉 Nome da coleção (slug Magic Eden): ").strip()
    url_colecao = construir_url_colecao(slug)
    print(f"[🌐] URL da coleção: {url_colecao}")

    iniciar_chrome_com_debug()
    time.sleep(5)
    driver = iniciar_navegador()

    print("[🚀] Faça login e conecte carteira no Chrome. Pressione ENTER para continuar...")
    input()

    while True:
        print("🔁 Novo ciclo iniciado.")
        driver.get(url_colecao)
        time.sleep(4)
        for _ in range(5):
            driver.execute_script("window.scrollBy(0, 1000);")
            time.sleep(1)

        precos = obter_precos_dos_cards(driver)
        if not precos:
            print("⚠️ Nenhum preço capturado — pulando ciclo.")
            time.sleep(INTERVALO_VERIFICACAO)
            continue

        print(f"💹 Preços em BTC: {precos}")
        preco_btc_usd = obter_preco_btc_usd()
        print(f"💵 Preço do BTC (USD): {preco_btc_usd}")

        sugestao = sugerir_preco_ia(precos, preco_btc_usd)
        if sugestao:
            print(f"💡 Sugestão da IA: {sugestao:.6f} BTC")
        else:
            print("⚠️ IA falhou em gerar sugestão válida.")

        valor_oferta = float(input("👉 Qual o valor da sua oferta? (em BTC): ").strip())

        for i in range(LIMITE_ITENS):
            try:
                driver.get(url_colecao)
                time.sleep(4)
                for _ in range(5):
                    driver.execute_script("window.scrollBy(0, 1000);")
                    time.sleep(1)

                cards = WebDriverWait(driver, 10).until(
                    EC.presence_of_all_elements_located((By.CSS_SELECTOR, "div[role='button'].flex.flex-col"))
                )
                if i >= len(cards):
                    print("⚠️ Menos itens do que o limite configurado.")
                    break

                card = cards[i]
                driver.execute_script("arguments[0].scrollIntoView();", card)
                time.sleep(1)
                card.click()
                time.sleep(3)

                botao_oferta = WebDriverWait(driver, 5).until(
                    EC.element_to_be_clickable((By.XPATH, "//button[contains(., 'Make an offer')]"))
                )
                botao_oferta.click()
                enviar_oferta(driver, valor_oferta)

            except Exception as e:
                print(f"⚠️ Erro ao interagir com o item {i+1}: {e}")

        print(f"⏳ Aguardando {INTERVALO_VERIFICACAO} segundos para novo ciclo...\n")
        time.sleep(INTERVALO_VERIFICACAO)

if __name__ == "__main__":
    executar_bot()
