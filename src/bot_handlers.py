# -*- coding: utf-8 -*-

import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, BotCommand
from telegram.ext import Application, ContextTypes
from telegram.constants import ParseMode

from . import scraper
from . import database
from .config import MAPA_CATEGORIAS

# Configuração do logger
logger = logging.getLogger(__name__)

# --- FUNÇÕES AUXILIARES ---

def get_sanitized_text(text: str) -> str:
    """Escapa caracteres especiais para o modo MarkdownV2 do Telegram."""
    escape_chars = r'_*[]()~`>#+-=|{}.!'
    return ''.join(f'\\{char}' if char in escape_chars else char for char in text)

async def enviar_resultados_cursos(update: Update, context: ContextTypes.DEFAULT_TYPE, cursos: list, titulo_header: str):
    """Envia uma lista de cursos formatada para o usuário."""
    chat_id = update.effective_chat.id

    if not cursos:
        await context.bot.send_message(chat_id=chat_id, text=f"Nenhum curso encontrado para '{titulo_header}'.")
        return

    await context.bot.send_message(
        chat_id=chat_id,
        text=f"🔎 *Resultados para '{get_sanitized_text(titulo_header)}'*",
        parse_mode=ParseMode.MARKDOWN_V2
    )

    for titulo, url in cursos[:10]:  # Limita a 10 resultados para não sobrecarregar o chat
        url_hash = str(hash(url))
        context.user_data[url_hash] = {'title': titulo, 'url': url}

        keyboard = InlineKeyboardMarkup([[
            InlineKeyboardButton("✅ Salvar na minha lista", callback_data=f"save:{url_hash}")
        ]])

        titulo_curto = (titulo[:75] + '...') if len(titulo) > 75 else titulo
        mensagem_curso = f"🎓 *{get_sanitized_text(titulo_curto)}*\n\n[Acessar Curso]({url})"

        await context.bot.send_message(
            chat_id=chat_id,
            text=mensagem_curso,
            reply_markup=keyboard,
            parse_mode=ParseMode.MARKDOWN_V2,
            disable_web_page_preview=True
        )

# --- HANDLERS DE COMANDOS ---

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler para o comando /start."""
    user = update.effective_user
    await update.message.reply_html(
        f"Olá, {user.mention_html()}!\n\n"
        "Eu sou seu assistente para encontrar cursos de TI. "
        "Use o menu de comandos (botão ` / `) ou digite um comando para começar."
    )

async def ajuda(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler para o comando /ajuda."""
    texto_ajuda = (
        "🤖 *Ajuda do Bot de Cursos de TI*\n\n"
        "Use os comandos abaixo para encontrar cursos:\n\n"
        "*/explorar_ti*\n"
        "Navegue por categorias \\(Programação, Redes, etc\\.\\) para ver cursos\\.\n\n"
        "*/pesquisar_cursos* `termo`\n"
        "Busca por um assunto específico\\.\n"
        "\\_Exemplo:_ `/pesquisar_cursos Python`\n\n"
        "*/cursos_pentest*\n"
        "Busca focada em Segurança da Informação e Pentest\\.\n\n"
        "*/meus_cursos*\n"
        "Mostra a sua lista de cursos salvos\\."
    )
    await update.message.reply_markdown_v2(texto_ajuda)

async def explorar_ti(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler para o comando /explorar_ti. Pergunta ao usuário o tipo de curso desejado."""
    keyboard = [
        [
            InlineKeyboardButton("💰 Cursos Pagos", callback_data='type_paid'),
            InlineKeyboardButton("🆓 Cursos Gratuitos", callback_data='type_free'),
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        "Ótima escolha! Para começar, você prefere explorar cursos pagos ou gratuitos?",
        reply_markup=reply_markup
    )

async def pesquisar_cursos(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler para o comando /pesquisar_cursos."""
    termo_busca = " ".join(context.args)
    if not termo_busca:
        await update.message.reply_text("Por favor, diga o que você quer aprender.\nExemplo: `/pesquisar_cursos Python`")
        return

    await update.message.reply_text(f"Buscando em todas as plataformas por '{termo_busca}', isso pode levar um momento...")
    # A busca direta pesquisa em todos os tipos de curso (gratuitos e pagos)
    resultados = await scraper.pesquisar_cursos_online(termo_busca, course_type="all")
    await enviar_resultados_cursos(update, context, resultados, termo_busca)

async def cursos_pentest(update: Update, context: ContextTypes.DEFAULT_TYPE, course_type: scraper.CourseType = "all"):
    """Handler para o comando /cursos_pentest, agora com filtro de tipo."""
    if isinstance(update, Update): # Se for chamado por um comando, não um botão
        await update.message.reply_text("Buscando cursos de Pentest e Hacking Ético, aguarde...")

    tipo_texto = "Pagos" if course_type == "paid" else "Gratuitos"
    if course_type == 'all':
        titulo_header = "Pentest & Hacking Ético"
    else:
        titulo_header = f"Pentest & Hacking Ético ({tipo_texto})"

    tasks = [
        scraper.pesquisar_cursos_pentest_especializados(course_type=course_type),
        scraper.pesquisar_cursos_online("pentest", course_type=course_type),
        scraper.pesquisar_cursos_online("ethical hacking", course_type=course_type)
    ]
    resultados_listas = await asyncio.gather(*tasks)

    todos_resultados = [curso for lista in resultados_listas for curso in lista]
    resultados_unicos = list(dict.fromkeys(todos_resultados))

    await enviar_resultados_cursos(update, context, resultados_unicos, titulo_header)

async def meus_cursos(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler para o comando /meus_cursos."""
    user_id = update.effective_user.id
    cursos_salvos = database.obter_cursos_usuario(user_id)

    if not cursos_salvos:
        await update.message.reply_text("Você ainda não salvou nenhum curso. Use o botão ✅ para criar sua lista!")
        return

    lista_formatada = ""
    for i, (titulo, url) in enumerate(cursos_salvos[:25], 1):
        titulo_curto = (titulo[:70] + '...') if len(titulo) > 70 else titulo
        lista_formatada += f"{i}\\. *[{get_sanitized_text(titulo_curto)}]({url})*\n"

    mensagem = f"📚 *Meus Cursos Salvos*\n\n{lista_formatada}"
    await update.message.reply_markdown_v2(mensagem, disable_web_page_preview=True)

# --- HANDLER DE CALLBACKS (BOTÕES) ---

async def button_callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Gerencia todos os cliques em botões inline."""
    query = update.callback_query
    await query.answer()
    data = query.data

    if data.startswith("save:"):
        await _handle_save_callback(query, context)
    elif data.startswith("type_"):
        await _handle_type_callback(query, context)
    elif data.startswith("cat_"):
        await _handle_category_callback(query, context)

async def _handle_type_callback(query: Update.callback_query, context: ContextTypes.DEFAULT_TYPE):
    """Lida com a escolha do tipo de curso (pago/gratuito) e mostra as categorias."""
    course_type = query.data.split("_", 1)[1]  # 'paid' or 'free'

    keyboard = [
        [InlineKeyboardButton("💻 Programação", callback_data=f'cat_{course_type}_programacao'), InlineKeyboardButton("🌐 Redes", callback_data=f'cat_{course_type}_redes')],
        [InlineKeyboardButton("☁️ Cloud", callback_data=f'cat_{course_type}_cloud'), InlineKeyboardButton("🛡️ Segurança", callback_data=f'cat_{course_type}_seguranca')],
        [InlineKeyboardButton("🗄️ Banco de Dados", callback_data=f'cat_{course_type}_dados'), InlineKeyboardButton("📊 Ciência de Dados", callback_data=f'cat_{course_type}_ciencia_dados')],
        [InlineKeyboardButton("⚙️ DevOps", callback_data=f'cat_{course_type}_devops')],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    tipo_texto = "Pagos" if course_type == "paid" else "Gratuitos"
    await query.edit_message_text(
        f"Excelente! Agora, escolha uma categoria de TI para ver os melhores cursos *{tipo_texto}*:",
        reply_markup=reply_markup,
        parse_mode=ParseMode.MARKDOWN_V2
    )

async def _handle_save_callback(query: Update.callback_query, context: ContextTypes.DEFAULT_TYPE):
    """Lida com o clique no botão 'Salvar'."""
    url_hash = query.data.split(":", 1)[1]

    if url_hash not in context.user_data:
        await query.edit_message_text(text=query.message.text + "\n\n❌ *Erro: Os dados deste curso expiraram. Por favor, faça a busca novamente.*", parse_mode=ParseMode.MARKDOWN_V2)
        return

    curso_info = context.user_data[url_hash]
    user_id = query.from_user.id

    if database.salvar_curso_usuario(user_id, curso_info['title'], curso_info['url']):
        await query.edit_message_text(text=query.message.text_markdown_v2 + "\n\n*✅ Curso salvo na sua lista\\!*", parse_mode=ParseMode.MARKDOWN_V2, disable_web_page_preview=True)
        await context.bot.answer_callback_query(callback_query_id=query.id, text="Curso salvo!", show_alert=False)
    else:
        await context.bot.answer_callback_query(callback_query_id=query.id, text="Você já salvou este curso!", show_alert=True)

async def _handle_category_callback(query: Update.callback_query, context: ContextTypes.DEFAULT_TYPE):
    """Lida com o clique em um botão de categoria, agora com tipo de curso."""
    # O formato do data é "cat_{course_type}_{category_key}"
    _, course_type, category_key = query.data.split("_", 2)

    # Caso especial para segurança
    if category_key == "seguranca":
        await query.edit_message_text(text="Buscando cursos de Segurança, por favor aguarde...")
        # Passa o tipo de curso para a função de pentest
        await cursos_pentest(query, context, course_type=course_type)
        return

    if category_key in MAPA_CATEGORIAS:
        termos, titulo_header = MAPA_CATEGORIAS[category_key]
        tipo_texto = "Pagos" if course_type == "paid" else "Gratuitos"
        titulo_completo = f"{titulo_header} ({tipo_texto})"

        await query.edit_message_text(text=f"Buscando em '{titulo_completo}', aguarde...")

        tasks = [scraper.pesquisar_cursos_online(termo, course_type=course_type) for termo in termos]
        resultados_listas = await asyncio.gather(*tasks)

        todos_resultados = [curso for lista in resultados_listas for curso in lista]
        resultados_unicos = list(dict.fromkeys(todos_resultados))

        await enviar_resultados_cursos(query, context, resultados_unicos, titulo_completo)

# --- CONFIGURAÇÃO DE COMANDOS ---

async def post_init(application: Application):
    """Define a lista de comandos do bot no Telegram após a inicialização."""
    commands = [
        BotCommand("start", "Inicia a conversa com o bot"),
        BotCommand("explorar_ti", "Navegue por categorias de cursos"),
        BotCommand("pesquisar_cursos", "Pesquise por um curso específico"),
        BotCommand("cursos_pentest", "Encontre cursos de segurança e pentest"),
        BotCommand("meus_cursos", "Veja sua lista de cursos salvos"),
        BotCommand("ajuda", "Mostra a mensagem de ajuda"),
    ]
    await application.bot.set_my_commands(commands)
    logger.info("Lista de comandos configurada no Telegram.")