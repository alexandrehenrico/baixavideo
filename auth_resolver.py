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
        """Estratégia Extrema: Camuflagem iOS/Safari (Legacy)"""
        opts = base_opts.copy()
        
        # 1. Network: Forçar IPv4
        opts['source_address'] = '0.0.0.0' 
        
        # 2. Client Impersonation: iOS é atualmente o mais difícil de bloquear
        opts['extractor_args'] = {
            'youtube': {
                'player_client': ['ios'],
                'player_skip': ['webcheck', 'js']
            }
        }
        
        # 3. Cookies
        if os.path.exists(self.cookies_path):
            opts['cookiefile'] = self.cookies_path
        
        # 4. User-Agent Safari/iPhone
        opts['user_agent'] = 'Mozilla/5.0 (iPhone; CPU iPhone OS 16_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Mobile/15E148 Safari/604.1'
        
        # 5. Reliability
        opts['nocheckcertificate'] = True
        opts['ignoreerrors'] = False # MUDANÇA: agora queremos ver o erro real no log se falhar
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
