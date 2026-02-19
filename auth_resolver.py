import os
import platform
import subprocess
import logging
import yt_dlp

class VisionXAuthResolver:
    def __init__(self, app_logger=None):
        self.logger = app_logger or logging.getLogger(__name__)
        self.os_name = platform.system()
        # Ensure path is absolute for reliability in cloud environments
        self.cookies_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'cookies.txt')

    def update_dependencies(self):
        """Attempts to update yt-dlp to latest version."""
        try:
            self.logger.info("Checking for yt-dlp updates...")
            subprocess.run(["pip", "install", "-U", "yt-dlp"], check=True, capture_output=True)
            self.logger.info("yt-dlp updated successfully.")
        except Exception as e:
            self.logger.error(f"Failed to update yt-dlp: {e}")

    def get_dynamic_opts(self, base_opts):
        """Estratégia de Sincronia: Windows/Chrome + Stealth"""
        opts = base_opts.copy()
        
        # 1. Network: Forçar IPv4
        opts['source_address'] = '0.0.0.0' 
        
        # 2. Client Impersonation: Usar o cliente web comum mas com bypass
        opts['extractor_args'] = {
            'youtube': {
                'player_client': ['web'],
                'skip': ['hls', 'dash']
            }
        }
        
        # 3. Cookies (Obrigatório para cloud)
        if os.path.exists(self.cookies_path):
            opts['cookiefile'] = self.cookies_path
        
        # 4. User-Agent: DEVE ser igual ao do navegador que gerou o cookies.txt
        opts['user_agent'] = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36'
        
        # 5. Opções de Stealth adicionais
        opts['referer'] = 'https://www.google.com/'
        opts['nocheckcertificate'] = True
        opts['geo_bypass'] = True
        
        return opts

    def log_safe(self, message):
        """Filter sensitive data from logs (like SIDs)"""
        # Basic filter for session tokens
        sensitive = ['SID', 'HSID', 'SSID', 'cookies']
        for s in sensitive:
            if s in message and 'download' not in message.lower():
                return f"[VisionX] Filtered sensitive diagnostic info"
        return message
