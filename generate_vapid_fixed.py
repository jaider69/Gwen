# generate_vapid_fixed.py
from ecdsa import SigningKey, NIST256p
import base64
import hashlib

def generate_vapid_keys():
    print("🎯 Generando claves VAPID con ecdsa...\n")
    
    # Generar par de claves
    private_key = SigningKey.generate(curve=NIST256p)
    public_key = private_key.get_verifying_key()
    
    # Convertir a bytes
    private_bytes = private_key.to_der()
    public_bytes = public_key.to_der()
    
    # Codificar a base64url (formato necesario para VAPID)
    def base64url_encode(data):
        return base64.urlsafe_b64encode(data).decode('utf-8').rstrip('=')
    
    # Formato PEM para la clave privada
    private_pem = "-----BEGIN PRIVATE KEY-----\n" + \
                  base64.b64encode(private_bytes).decode('utf-8') + \
                  "\n-----END PRIVATE KEY-----\n"
    
    # Formato para la clave pública (sin PEM, directamente base64url)
    public_b64url = base64url_encode(public_bytes)
    
    print("=" * 70)
    print("🔐 CLAVE PRIVADA (para .env o app.py):")
    print("=" * 70)
    print(private_pem)
    
    print("\n" + "=" * 70)
    print("🔓 CLAVE PÚBLICA (para gwen.html):")
    print("=" * 70)
    print(public_b64url)
    
    print("\n" + "=" * 70)
    print("📋 FORMATO LISTO PARA COPIAR:")
    print("=" * 70)
    
    # Para .env (en una sola línea con \n)
    private_oneline = private_pem.replace('\n', '\\n')
    
    print('# Añade esto a tu archivo .env:')
    print(f'VAPID_PRIVATE_KEY="{private_oneline}"')
    print(f'VAPID_PUBLIC_KEY="{public_b64url}"')
    
    print('\n# O si usas directamente en app.py:')
    print(f'VAPID_PRIVATE_KEY = """{private_pem}"""')
    print(f'VAPID_PUBLIC_KEY = "{public_b64url}"')
    
    # Verificación
    print("\n" + "=" * 70)
    print("✅ VERIFICACIÓN:")
    print("=" * 70)
    print(f"Longitud clave privada: {len(private_pem)} caracteres")
    print(f"Longitud clave pública: {len(public_b64url)} caracteres")
    print("\nSi la clave pública empieza con 'BM' o 'BN' y tiene ~87 caracteres, es correcta.")

if __name__ == "__main__":
    generate_vapid_keys()