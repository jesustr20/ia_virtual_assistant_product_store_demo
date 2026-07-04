import random
from typing import Optional

class AIHandler:
    def __init__(self):
        self.greeting_phrases = [
            "¡Hola! 😊 Bienvenido a nuestra tienda. Estoy aquí para ayudarte.",
            "Hola, bienvenido. ¿En qué puedo asistirte hoy?",
            "¡Hola! Dime, ¿qué necesitas?"
        ]
        self.default_phrases = [
            "Hmm... no estoy seguro de eso, pero puedo intentarlo.",
            "¿Podrías explicarlo de otra manera? Quiero ayudarte lo mejor posible.",
            "Déjame buscar esa información para ti, un momento por favor."
        ]
        self.product_phrases = [
            "¡Claro! Permíteme verificar nuestra lista de productos.",
            "Voy a revisar nuestra base de datos de productos, por favor espera un momento.",
            "Sí, tenemos productos disponibles. Déjame confirmarte los detalles."
        ]
    
    def generate_humanlike_response(self, user_input: str, product_info: Optional[str] = None) -> str:
        if self._is_greeting(user_input):
            return random.choice(self.greeting_phrases)
        
        if product_info:
            return random.choice(self.product_phrases)
    
        return random.choice(self.default_phrases)
    
    def _is_greeting(self, user_input: str) -> bool:
        greetings = ["hola", "buenos días", "buenas tardes", "hey", "qué tal", "hi"]
        user_input_lower = user_input.lower()
        return any(greet in user_input_lower for greet in greetings)