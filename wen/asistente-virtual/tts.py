from gtts import gTTS
import os
import time
import pygame

# Inicializar pygame mixer una sola vez al importar
try:
    pygame.mixer.init()
    print("🔊 Pygame mixer inicializado")
except Exception as e:
    print(f"❌ Error inicializando pygame: {e}")

class TTS():
    def __init__(self):
        self.is_playing = False
    
    def process(self, text):
        try:
            # Crear directorio static si no existe
            os.makedirs("static", exist_ok=True)
            
            # Usar nombre único para evitar conflictos
            timestamp = str(int(time.time()))
            file_name = f"response_{timestamp}.mp3"
            file_path = os.path.join("static", file_name)
            
            print(f"🔊 Generando audio para: {text}")
            
            # Generar audio
            tts = gTTS(text=text, lang='es', slow=False)
            tts.save(file_path)
            print(f"✅ Audio guardado: {file_path}")
            
            # Reproducir audio
            success = self.play_audio(file_path)
            
            if success:
                # Esperar un poco antes de eliminar el archivo
                time.sleep(2)
                # Intentar eliminar el archivo temporal
                try:
                    if os.path.exists(file_path):
                        os.remove(file_path)
                        print(f"🗑️ Archivo temporal eliminado: {file_path}")
                except:
                    print(f"⚠️ No se pudo eliminar el archivo temporal: {file_path}")
            
            return file_name
            
        except Exception as e:
            print(f"❌ Error generando audio: {e}")
            import traceback
            traceback.print_exc()
            return "response.mp3"
    
    def play_audio(self, file_path):
        """Reproducir audio con pygame"""
        try:
            if not os.path.exists(file_path):
                print(f"❌ Archivo no encontrado: {file_path}")
                return False
            
            # Esperar si ya se está reproduciendo algo
            while self.is_playing:
                time.sleep(0.1)
            
            self.is_playing = True
            
            # Cargar y reproducir
            pygame.mixer.music.load(file_path)
            pygame.mixer.music.play()
            print("🔊 Reproduciendo audio...")
            
            # Esperar a que termine la reproducción
            while pygame.mixer.music.get_busy():
                time.sleep(0.1)
            
            print("✅ Audio reproducido correctamente")
            self.is_playing = False
            return True
            
        except Exception as e:
            print(f"❌ Error reproduciendo audio: {e}")
            self.is_playing = False
            return False