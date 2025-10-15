# -*- coding: utf-8 -*-

import logging
from telegram.ext import Application, CommandHandler, CallbackQueryHandler

from .config import TOKEN
from . import database
from . import bot_handlers

# --- CONFIGURAÇÃO DE LOGS ---
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
# Reduz o log excessivo da biblioteca httpcore, que é usada pelo httpx/telegram.ext
logging.getLogger("httpcore").setLevel(logging.WARNING)
logger = logging.getLogger(__name__)

def main():
    """Função principal que inicia o bot."""
    if not TOKEN:
        logger.critical("ERRO CRÍTICO: A variável de ambiente TELEGRAM_TOKEN não foi configurada.")
        return

    # Inicia o banco de dados antes de tudo
    try:
        database.iniciar_banco_de_dados()
    except Exception as e:
        logger.critical(f"Não foi possível iniciar o banco de dados. O bot não pode continuar. Erro: {e}")
        return

    # Cria a aplicação do bot
    application = Application.builder().token(TOKEN).post_init(bot_handlers.post_init).build()

    # Registra todos os handlers de comando
    application.add_handler(CommandHandler("start", bot_handlers.start))
    application.add_handler(CommandHandler("ajuda", bot_handlers.ajuda))
    application.add_handler(CommandHandler("explorar_ti", bot_handlers.explorar_ti))
    application.add_handler(CommandHandler("pesquisar_cursos", bot_handlers.pesquisar_cursos))
    application.add_handler(CommandHandler("cursos_pentest", bot_handlers.cursos_pentest))
    application.add_handler(CommandHandler("meus_cursos", bot_handlers.meus_cursos))

    # Registra o handler para os botões (callbacks)
    application.add_handler(CallbackQueryHandler(bot_handlers.button_callback_handler))

    logger.info("Bot do Telegram iniciado. Pressione Ctrl+C para parar.")

    # Inicia o polling para receber atualizações do Telegram
    application.run_polling()

if __name__ == '__main__':
    main()