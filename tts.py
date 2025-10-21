from gtts import gTTS
import os
import time
import pygame
import tempfile

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
        """Generar y reproducir audio SIN guardar archivos permanentes"""
        temp_file = None
        try:
            print(f"🔊 Generando audio para: {text}")
            
            # Crear archivo temporal que se eliminará automáticamente
            with tempfile.NamedTemporaryFile(delete=False, suffix='.mp3') as temp:
                temp_file = temp.name
            
            # Generar audio
            tts = gTTS(text=text, lang='es', slow=False)
            tts.save(temp_file)
            print(f"✅ Audio temporal generado")
            
            # Reproducir audio
            success = self.play_audio(temp_file)
            
            # ELIMINAR el archivo temporal después de reproducir
            if temp_file and os.path.exists(temp_file):
                try:
                    # Esperar un momento para asegurar que terminó la reproducción
                    time.sleep(0.5)
                    os.remove(temp_file)
                    print(f"🗑️ Archivo temporal eliminado")
                except Exception as e:
                    print(f"⚠️ No se pudo eliminar archivo temporal: {e}")
            
            return "audio_temporal"
            
        except Exception as e:
            print(f"❌ Error generando audio: {e}")
            import traceback
            traceback.print_exc()
            
            # Limpiar archivo temporal en caso de error
            if temp_file and os.path.exists(temp_file):
                try:
                    os.remove(temp_file)
                except:
                    pass
            
            return None
    
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