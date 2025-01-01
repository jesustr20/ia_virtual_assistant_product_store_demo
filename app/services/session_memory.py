class SessionMemory:
    def __init__(self):
        self.interactions = []

    def save_interaction(self, question: str, response: str):        
        self.interactions.append({"question": question, "response": response})
    
    def get_context(self) -> str:
        if not self.interactions:
            return "No hay contexto previo."
        recent_interactions = self.interactions[-3:]
        return "Contexto reciente\n" + "\n".join(
            [f"Pregunta: {i['question']} | Respuesta: {i['response']}" for i in recent_interactions]
        )