import google.generativeai as genai
from .session_memory import SessionMemory
from ..repositories import ProductRepository
from ..services.ai_handler import AIHandler

class GeminiService:
    def __init__(self, api_key: str, product_repo: ProductRepository):
        genai.configure(api_key=api_key)
        self.product_repo = product_repo        
        self.model = genai.GenerativeModel("gemini-1.5-flash")
        self.ai_handler = AIHandler()
        self.session_memory = SessionMemory()

    def get_humanlike_response(self, question: str):
        
        context = self.session_memory.get_context()
        
        processed_question = self.ai_handler.generate_humanlike_response(question)
        
        prompt = (
            f"{context}\n"
            f"Eres un asistente virtual de una tienda online. Tu objetivo es ayudar a los usuarios "
            f"de manera clara y amigable.\n"
            f"Pregunta: '{processed_question}'\nRespuesta:"
        )
        
        response = self.model.generate_content(prompt)
        ia_response = response._result.candidates[0].content.parts[0].text

        self.session_memory.save_interaction(question, ia_response)
        return ia_response
    
    def respond_with_products(self, question: str):
        
        context = self.session_memory.get_context()

        products = self.product_repo.get_products()

        if not products:
            prompt = (
                f"{context}\n"
                f"Eres un asistente virtual de una tienda online. El usuario preguntó: '{question}'.\n"
                "Por ahora no hay productos disponibles. Responde de forma clara y sugiere al usuario "
                "que vuelva más tarde para revisar nuestras novedades."
            )
        else:
            product_info = "\n".join([f"{p.name}: {p.description} a {p.price} SOL" for p in products])
            prompt = (
                f"{context}\n"
                f"El usuario preguntó: '{question}'.\n"
                f"Productos disponibles:\n{product_info}\n"
                "Responde mostrando los productos de forma natural y amigable."
            )
       
        response = self.model.generate_content(prompt)

        ia_response = response._result.candidates[0].content.parts[0].text

        self.session_memory.save_interaction(question, ia_response)
        return ia_response