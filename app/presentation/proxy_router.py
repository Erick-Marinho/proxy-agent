from fastapi import APIRouter, HTTPException, Depends
import time
from app.application.agent.proxy_agent_builder import ProxyAgentBuilder
from langchain_core.messages import HumanMessage, SystemMessage
import logging
from app.model.chat_request import ChatRequest
from app.model.chat_response import ChatResponse
import os
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from langgraph.store.postgres.aio import AsyncPostgresStore

logger = logging.getLogger(__name__)

router = APIRouter()

@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """
    Endpoint para conversar com o proxy agent supervisor
    """
    start_time = time.time()
    
    
    try:
        message_text = request.message
        phone = request.phone
        thread_id = phone
        user_id = phone

        logger.info(f"Pergunta recebida: {message_text} - {phone} - {thread_id}")

        dsn = os.getenv("DB_URI")

        async with (
            AsyncPostgresStore.from_conn_string(dsn) as store, 
            AsyncPostgresSaver.from_conn_string(dsn) as checkpointer
            ):
            #await store.setup()
            #await checkpointer.setup()

            # Cria supervisor a cada requisição (evita cache)
            proxy_supervisor = ProxyAgentBuilder().compile(checkpointer=checkpointer, store=store)

            # Cria namespace para memórias por usuário
            namespace = ("memories", user_id)

            try:
                memories = await store.asearch(namespace, query=str(message_text))
            except TypeError:
                # Compatibilidade caso a assinatura exija parâmetros nomeados diferentes
                memories = await store.asearch(namespace=namespace, query=str(message_text))
            info = "\n".join([m.value.get("data", "") for m in (memories or []) if m and getattr(m, "value", None)])

            system_msg = ""
            if info:
                system_msg = f"Você é um assistente útil. Informações do usuário: {info}"

            persona_msg = (
                "Adote a persona 'Yasmin - Doutor Sofá'. "
                "Na primeira resposta, cumprimente cordialmente e apresente-se como Yasmin; "
                "não solicite foto do item nesta etapa; pergunte de forma objetiva qual item deseja higienizar. "
                "Para orçamento e agendamento, o supervisor fará o encaminhamento apropriado. "
                "Não reescreva respostas dos especialistas; repasse-as exatamente ao usuário. "
                "Não antecipe coleta de dados; aguarde o fluxo automático."
                "Evite repetir conteúdo idêntico já enviado nesta conversa."
            )

            # Se o usuário pedir para lembrar algo, persistir memória simples
            lower = (message_text or "").lower()
            if "lembre" in lower or "remember" in lower:
                # Heurística: extrair após ':' se existir
                to_remember = message_text.split(":", 1)[-1].strip() if ":" in message_text else message_text
                await store.aput(namespace, str(__import__("uuid").uuid4()), {"data": to_remember})

            # Cria estado inicial com SystemMessage (se existir) + HumanMessage
            messages_init = []

            if persona_msg:
                messages_init.append(SystemMessage(content=persona_msg))

            if system_msg:
                messages_init.append(SystemMessage(content=system_msg))
            messages_init.append(HumanMessage(content=request.message))

            # Cria estado inicial
            initial_state = {"messages": messages_init}

            config = {"configurable": {"thread_id": thread_id, "user_id": user_id}}
            
            # Executa o supervisor
            result = await proxy_supervisor.ainvoke(initial_state, config=config )
        
            # Extrai resposta final e agente usado de forma simples
            messages = result.get("messages", [])
            last_message = messages[-1]
            response_text = last_message.content
            
            logger.info(f"Requisição processada - Thread ID: {thread_id}")

        total_time = time.time() - start_time
        
        return ChatResponse(
            message=response_text,
            phone=request.phone,
            execution_time=f"{total_time:.2f}s",
        )
        
    except Exception as e:
        # Captura stacktrace completo para diagnóstico
        import traceback
        logger.error(f"Erro no chat: {str(e)}")
        logger.error(f"Stacktrace completo: {traceback.format_exc()}")
        total_time = time.time() - start_time
        return ChatResponse(
            message="Desculpe, ocorreu um erro interno.",
            phone=request.phone,
            execution_time=f"{total_time:.2f}s",
        )