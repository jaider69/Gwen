import speech_recognition as sr
import time

def test_microphone():
    """Script de prueba para verificar la detección del micrófono"""
    
    print("\n" + "="*60)
    print("🎤 PRUEBA DE MICRÓFONO PARA GWEN")
    print("="*60)
    
    recognizer = sr.Recognizer()
    microphone = sr.Microphone()
    
    # Listar micrófonos disponibles
    print("\n📋 Micrófonos disponibles:")
    for index, name in enumerate(sr.Microphone.list_microphone_names()):
        print(f"   [{index}] {name}")
    
    # Calibración
    print("\n🔧 Calibrando micrófono...")
    with microphone as source:
        recognizer.adjust_for_ambient_noise(source, duration=2)
    
    print(f"✅ Energy threshold inicial: {recognizer.energy_threshold}")
    
    # Ajustar manualmente
    recognizer.energy_threshold = 200
    recognizer.pause_threshold = 0.8
    recognizer.dynamic_energy_threshold = True
    
    print(f"✅ Energy threshold ajustado: {recognizer.energy_threshold}")
    print(f"✅ Pause threshold: {recognizer.pause_threshold}")
    
    print("\n" + "="*60)
    print("🎯 Di 'GWEN' seguido de un comando")
    print("   Ejemplo: 'Gwen agrega 5 arroz'")
    print("   Presiona Ctrl+C para salir")
    print("="*60 + "\n")
    
    test_count = 0
    success_count = 0
    
    try:
        while True:
            test_count += 1
            print(f"\n[Prueba #{test_count}] 🎤 Escuchando...")
            
            try:
                with microphone as source:
                    # Ajuste rápido
                    recognizer.adjust_for_ambient_noise(source, duration=0.3)
                    
                    # Escuchar
                    audio = recognizer.listen(source, timeout=3, phrase_time_limit=10)
                    
                print(f"   📊 Audio capturado: {len(audio.frame_data)} bytes")
                
                # Transcribir
                try:
                    text = recognizer.recognize_google(audio, language='es-ES')
                    print(f"   ✅ DETECTADO: '{text}'")
                    
                    # Verificar si tiene "gwen" o variantes
                    text_lower = text.lower()
                    wake_words = ['gwen', 'guen', 'wen', 'when', 'buen', 'bwen', 
                                 'bendy', 'bendi', 'wendy', 'wendi']
                    
                    found = False
                    for wake in wake_words:
                        if wake in text_lower:
                            print(f"   🎉 ¡WAKE WORD ENCONTRADA: '{wake}'!")
                            success_count += 1
                            found = True
                            break
                    
                    if not found:
                        print(f"   ⚠️  No se detectó wake word en: '{text}'")
                    
                    print(f"   📈 Tasa de éxito: {success_count}/{test_count} ({success_count*100//test_count if test_count > 0 else 0}%)")
                    
                except sr.UnknownValueError:
                    print(f"   ❓ No se entendió el audio")
                except sr.RequestError as e:
                    print(f"   ❌ Error de Google API: {e}")
                
                time.sleep(0.5)
                
            except sr.WaitTimeoutError:
                print(f"   ⏱️  Timeout - no se detectó audio")
                continue
                
    except KeyboardInterrupt:
        print(f"\n\n{'='*60}")
        print(f"📊 RESUMEN DE PRUEBAS")
        print(f"{'='*60}")
        print(f"   Total de intentos: {test_count}")
        print(f"   Wake words detectadas: {success_count}")
        print(f"   Tasa de éxito: {success_count*100//test_count if test_count > 0 else 0}%")
        print(f"{'='*60}\n")

if __name__ == "__main__":
    test_microphone()