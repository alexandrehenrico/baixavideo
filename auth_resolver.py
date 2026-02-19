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
        """Applies advanced stealth and client rotation logic."""
        opts = base_opts.copy()
        
        # 1. Network Strategy: Force IPv4
        opts['source_address'] = '0.0.0.0' 
        
        # 2. Client Impersonation Strategy (CRITICAL)
        # We tell YouTube we are an Android App or a TV, which has less bot protection than Web.
        opts['extractor_args'] = {
            'youtube': {
                'player_client': ['android', 'web_embedded'],
                'skip': ['dash', 'hls']
            }
        }
        
        # 3. Authentication (Cookies)
        if os.path.exists(self.cookies_path):
            self.logger.info(f"Applying cookies from {self.cookies_path}")
            opts['cookiefile'] = self.cookies_path
        
        # 4. Stealth Headers: Impersonate a real mobile device
        opts['user_agent'] = 'com.google.android.youtube/19.05.36 (Linux; U; Android 11; pt_BR; Pixel 5 Build/RD2A.211001.002) gzip'
        
        # 5. Extraction reliability
        opts['nocheckcertificate'] = True
        opts['ignoreerrors'] = True
        opts['no_color'] = True
        
        # 6. Bypass geographical blocks
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
