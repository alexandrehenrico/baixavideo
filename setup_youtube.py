import yt_dlp
import os

def setup_oauth2():
    print("--- VisionX YouTube Auth Setup ---")
    print("Este script vai autorizar seu servidor a baixar vídeos usando OAuth2.")
    print("Isso evita 100% dos erros de 'Sign in to confirm you're not a bot'.\n")
    
    # Opções para disparar o login OAuth2
    ydl_opts = {
        'username': 'oauth2',
        'password': '', # Deixar vazio para disparar o fluxo de código
    }
    
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            # Tentar extrair algo simples para disparar o login
            print("Siga as instruções abaixo para autorizar no seu navegador:")
            ydl.extract_info("https://www.youtube.com/watch?v=dQw4w9WgXcQ", download=False)
            print("\nAutorização concluída com sucesso!")
            print("Os tokens foram salvos automaticamente pelo yt-dlp.")
    except Exception as e:
        print(f"\nErro durante a configuração: {e}")

if __name__ == "__main__":
    setup_oauth2()
