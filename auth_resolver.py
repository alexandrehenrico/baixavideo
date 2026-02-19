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
        """Applies intelligent bypass and authentication logic."""
        opts = base_opts.copy()
        
        # 1. Network Strategy: Force IPv4 to bypass many cloud/data-center blocks
        opts['source_address'] = '0.0.0.0' 
        
        # 2. Authentication Strategy
        if os.path.exists(self.cookies_path):
            self.logger.info(f"Using cookie persistence from {self.cookies_path} (Cloud/Manual Mode)")
            opts['cookiefile'] = self.cookies_path
        else:
            # Local Dev Mode: Try to detect active browser sessions
            self.logger.info("No cookies.txt found. Attempting to capture local browser sessions...")
            browsers = ['chrome', 'edge', 'firefox', 'brave', 'opera', 'chromium']
            
            for browser in browsers:
                # We try one by one. If it fails (like on a headless server), we just ignore it.
                # Note: On Linux/Headless without browsers, this will safely be ignored.
                # On Windows/local, it will try to "steal" the session.
                try:
                    # We don't actually set it here yet, because yt-dlp might fail late.
                    # We'll stick to a simpler logic of checking if we are on Windows first.
                    if self.os_name == 'Windows':
                        opts['cookiesfrombrowser'] = (browser, None, None, None)
                        self.logger.info(f"Using session from {browser}")
                        break
                except:
                    continue
        
        # 3. Impersonate Real Browser
        opts['user_agent'] = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        
        # 4. Better extraction reliability
        opts['nocheckcertificate'] = True
        
        return opts

    def log_safe(self, message):
        """Filter sensitive data from logs (like SIDs)"""
        # Basic filter for session tokens
        sensitive = ['SID', 'HSID', 'SSID', 'cookies']
        for s in sensitive:
            if s in message and 'download' not in message.lower():
                return f"[VisionX] Filtered sensitive diagnostic info"
        return message
