#import requests
from langchain_core.tools import tool
import logging

logger = logging.getLogger(__name__)

@tool
def calculate_math(operation: str) -> str:
    """
    Executa cálculos matemáticos. Use para operações como soma, subtração, 
    multiplicação, divisão e outras operações matemáticas.
    Retorna o resultado final do cálculo.
    """
    logger.info(f"Calculando a operação: {operation}")
    
    try:
        # Simula chamada para agente matemático externo
        # response = requests.post(
        #     "http://localhost:8001/calculate",
        #     json={"operation": operation},
        #     timeout=30
        # )
        # result = response.json()
        
        # Por enquanto, faz cálculo simples localmente para evitar loops
        try:
            # Tenta avaliar expressões matemáticas simples
            if any(op in operation for op in ['+', '-', '*', '/', 'x']):
                # Limpa a string e tenta calcular
                clean_operation = operation.replace('x', '*').replace(' ', '')
                
                # Para segurança, apenas operações básicas
                if all(c in '0123456789+-*/.() ' for c in clean_operation):
                    result = eval(clean_operation)
                    return f"O resultado de {operation} é {result}."
                else:
                    return f"Calculando {operation}: [resultado simulado - substitua pela API real]"
            else:
                return f"Operação '{operation}' processada: [resultado simulado]"
                
        except:
            # Se falhar, retorna simulado
            return f"Resultado calculado para '{operation}': [simulado - substitua pela API real]"
        
    except Exception as e:
        logger.error(f"Erro ao calcular a operação: {e}")
        return f"Erro ao calcular: {operation}"
