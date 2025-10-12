from groq import Groq
import json
import os
from dotenv import load_dotenv

class LLM():
    def __init__(self, groq_client=None):
        load_dotenv()
        
        if groq_client:
            self.client = groq_client
        else:
            api_key = os.getenv('GROQ_API_KEY')
            if not api_key:
                print("❌ ERROR: GROQ_API_KEY no encontrada en .env")
                raise ValueError("GROQ_API_KEY no configurada")
            print(f"✅ Groq LLM - API Key cargada: {api_key[:20]}...")
            self.client = Groq(api_key=api_key)
    
    def process_functions(self, text):
        try:
            response = self.client.chat.completions.create(
                model="llama-3.1-70b-versatile",
                messages=[
                    {"role": "system", "content": "Eres un asistente útil y eficiente"},
                    {"role": "user", "content": text},
                ],
                tools=[
                    {
                        "type": "function",
                        "function": {
                            "name": "get_weather",
                            "description": "Obtener el clima actual de una ciudad",
                            "parameters": {
                                "type": "object",
                                "properties": {
                                    "ubicacion": {
                                        "type": "string",
                                        "description": "La ubicación, debe ser una ciudad",
                                    }
                                },
                                "required": ["ubicacion"],
                            },
                        }
                    },
                    {
                        "type": "function",
                        "function": {
                            "name": "open_chrome",
                            "description": "Abrir el explorador Chrome en un sitio web específico",
                            "parameters": {
                                "type": "object",
                                "properties": {
                                    "website": {
                                        "type": "string",
                                        "description": "La URL del sitio web al cual se desea ir"
                                    }
                                },
                                "required": ["website"]
                            }
                        }
                    },
                ],
                tool_choice="auto",
            )
            
            message = response.choices[0].message
            
            if message.tool_calls:
                tool_call = message.tool_calls[0]
                function_name = tool_call.function.name
                args = json.loads(tool_call.function.arguments)
                print(f"✅ Función a llamar: {function_name}")
                print(f"📋 Argumentos: {args}")
                return function_name, args, message
            
            print("ℹ️ No se llamó ninguna función, respuesta directa")
            return None, None, message
            
        except Exception as e:
            print(f"❌ Error en process_functions: {e}")
            import traceback
            traceback.print_exc()
            return None, None, None
    
    def process_response(self, text, message, function_name, function_response):
        try:
            # Construir mensaje de herramienta
            tool_message = {
                "role": "tool",
                "tool_call_id": message.tool_calls[0].id,
                "name": function_name,
                "content": function_response,
            }
            
            response = self.client.chat.completions.create(
                model="llama-3.1-70b-versatile",
                messages=[
                    {"role": "system", "content": "Eres un asistente útil y eficiente"},
                    {"role": "user", "content": text},
                    message,
                    tool_message,
                ],
            )
            return response.choices[0].message.content
        except Exception as e:
            print(f"❌ Error en process_response: {e}")
            import traceback
            traceback.print_exc()
            return f"Error al procesar la respuesta: {str(e)}"