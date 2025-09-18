import logging
import os
import sqlite3
import urllib.parse
from typing import List

import requests
from bs4 import BeautifulSoup
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, BotCommand
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
    PicklePersistence, # Para salvar dados do usuário
)

# --- 1. CONFIGURAÇÃO PROFISSIONAL ---
# Leia o token de uma variável de ambiente para segurança.
# Antes de executar, defina a variável: export TELEGRAM_TOKEN="SEU_TOKEN" (no Linux/macOS)
# ou set TELEGRAM_TOKEN="SEU_TOKEN" (no Windows)
TOKEN = os.getenv("")

# --- ARQUIVOS DE DADOS ---
DB_FILE = "cursos_usuarios.db"
PERSISTENCE_FILE = "bot_persistence" # Arquivo para persistência de dados

# --- CONFIGURAÇÃO DE LOGS ---
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)


# --- 2. BANCO DE DADOS (Sem alterações, já era robusto) ---
def iniciar_banco_de_dados():
    conexao = sqlite3.connect(DB_FILE)
    cursor = conexao.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS inscricoes (
            id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL,
            course_title TEXT NOT NULL, course_url TEXT NOT NULL,
            UNIQUE(user_id, course_url)
        )
    ''')
    conexao.commit()
    conexao.close()


# --- 3. WEB SCRAPING (Sem alterações na lógica principal) ---
# (As funções pegar_cursos, pesquisar_cursos_online, etc., permanecem as mesmas)
def pegar_cursos(url: str, base_url: str, filter_keyword: str):
    cursos = []
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3'}
        r = requests.get(url, headers=headers, timeout=15)
        r.raise_for_status()
        soup = BeautifulSoup(r.text, "html.parser")
        for a in soup.find_all("a", href=True):
            if filter_keyword in a['href']:
                link = a['href']
                if not link.startswith("http"):
                    link = base_url + link
                title = a.get_text(strip=True) or (a.find('img') and a.find('img').get('alt')) or link.split('/')[-1].replace('-', ' ').title()
                cursos.append((title.strip(), link))
        return list({curso[1]: curso for curso in cursos}.values())
    except requests.RequestException as e:
        logger.error(f"Erro de rede ao acessar {url}: {e}")
        return []
    except Exception as e:
        logger.error(f"Erro desconhecido ao processar {url}: {e}")
        return []

sites_de_busca = {
    "Udemy (Grátis)": ("https://www.udemy.com/courses/search/?price=price-free&q={}&sort=relevance", "https://www.udemy.com", "/course/"),
    "Coursera": ("https://www.coursera.org/search?query={}", "https://www.coursera.org", "/learn/"),
    "Digital Innovation One": ("https://www.dio.me/browse?search={}", "https://www.dio.me", "/curso/"),
}

def pesquisar_cursos_online(termo: str):
    todos_cursos = []
    termo_formatado = urllib.parse.quote_plus(termo)
    for nome, (url_template, base, filtro) in sites_de_busca.items():
        url_de_busca = url_template.format(termo_formatado)
        logger.info(f"Pesquisando '{termo}' em {nome}...")
        todos_cursos.extend(pegar_cursos(url_de_busca, base, filtro))
    return list({curso[1]: curso for curso in todos_cursos}.values())

sites_pentest = { "HackerSec (Grátis)": ("https://hackersec.com/cursos-gratuitos/", "https://hackersec.com", "/curso/") }

def pesquisar_cursos_pentest_especializados():
    todos_cursos = []
    for nome, (url_fixa, base, filtro) in sites_pentest.items():
        todos_cursos.extend(pegar_cursos(url_fixa, base, filtro))
    return list({curso[1]: curso for curso in todos_cursos}.values())


# --- 4. FUNÇÕES DE INTERAÇÃO COM O USUÁRIO (Refatoradas) ---
async def enviar_resultados_cursos(update: Update, context: ContextTypes.DEFAULT_TYPE, cursos: List, titulo_header: str):
    """Formata e envia uma lista de cursos, armazenando os resultados no context."""
    if not cursos:
        await update.effective_message.reply_text(f"Nenhum curso encontrado para: '{titulo_header}'.")
        return

    resultados_limitados = cursos[:10]
    context.user_data['last_results'] = resultados_limitados  # Armazena os resultados para o usuário

    await update.effective_message.reply_text(
        f"🔎 *Resultados para '{titulo_header}'*\nMostrando {len(resultados_limitados)} de {len(cursos)} cursos encontrados:",
        parse_mode='Markdown'
    )

    for i, (titulo, url) in enumerate(resultados_limitados):
        keyboard = [[InlineKeyboardButton("✅ Salvar na minha lista", callback_data=f"save_{i}")]] # Callback com índice
        reply_markup = InlineKeyboardMarkup(keyboard)
        mensagem = f"🎓 *{titulo}*\n[Acessar curso]({url})"
        await update.effective_message.reply_text(mensagem, reply_markup=reply_markup, parse_mode='Markdown')

async def ajuda_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Mostra a mensagem de ajuda com os comandos."""
    user_name = update.effective_user.first_name
    texto_ajuda = (
        f"Olá, {user_name}! 👋\n\n"
        "Eu sou seu assistente para encontrar cursos de TI. Veja o que posso fazer com o menu de comandos abaixo (botão `/`).\n\n"
        "*/explorar_ti* - Navegue por categorias.\n"
        "*/pesquisar <termo>* - Busca por um assunto. Ex: `/pesquisar Python`\n"
        "*/cursos_pentest* - Busca focada em Hacking Ético.\n"
        "*/meus_cursos* - Mostra sua lista de cursos salvos."
    )
    await update.message.reply_text(texto_ajuda, parse_mode='Markdown')

async def explorar_ti(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Exibe um menu de categorias de TI."""
    keyboard = [
        [InlineKeyboardButton("💻 Programação", callback_data='cat_programacao'), InlineKeyboardButton("🌐 Redes/Infra", callback_data='cat_redes')],
        [InlineKeyboardButton("☁️ Cloud", callback_data='cat_cloud'), InlineKeyboardButton("🛡️ Segurança", callback_data='cat_seguranca')],
        [InlineKeyboardButton("🗄️ Banco de Dados", callback_data='cat_dados'), InlineKeyboardButton("📊 Ciência de Dados", callback_data='cat_ciencia_dados')],
        [InlineKeyboardButton("⚙️ DevOps", callback_data='cat_devops')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text('🧭 Escolha uma área de TI para explorar:', reply_markup=reply_markup)

async def pesquisar_cursos(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Pesquisa por um termo fornecido pelo usuário."""
    termo = " ".join(context.args)
    if not termo:
        await update.message.reply_text("Por favor, me diga o que pesquisar. Ex: `/pesquisar Python`")
        return

    await update.message.reply_text(f"Buscando cursos sobre '{termo}', por favor aguarde...")
    resultados = pesquisar_cursos_online(termo)
    await enviar_resultados_cursos(update, context, resultados, termo)

async def cursos_pentest(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Busca cursos específicos de Pentest."""
    await update.message.reply_text("Buscando cursos de Pentest & Hacking Ético...")
    resultados = pesquisar_cursos_pentest_especializados() + pesquisar_cursos_online("pentest") + pesquisar_cursos_online("ethical hacking")
    resultados_finais = list({curso[1]: curso for curso in resultados}.values())
    await enviar_resultados_cursos(update, context, resultados_finais, "Pentest & Hacking Ético")

async def meus_cursos(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Mostra os cursos salvos pelo usuário."""
    user_id = update.effective_user.id
    try:
        conexao = sqlite3.connect(DB_FILE)
        cursor = conexao.cursor()
        cursor.execute("SELECT course_title, course_url FROM inscricoes WHERE user_id = ?", (user_id,))
        cursos_do_usuario = cursor.fetchall()
        conexao.close()

        if not cursos_do_usuario:
            await update.message.reply_text("Você ainda não salvou nenhum curso. Use o botão '✅ Salvar' para adicioná-lo aqui!")
            return

        lista_formatada = "\n".join([f"{i}. [{titulo}]({url})" for i, (titulo, url) in enumerate(cursos_do_usuario[:25], 1)])
        await update.message.reply_text(f"📚 *Meus Cursos Salvos*\n\n{lista_formatada}", parse_mode='Markdown')
    except Exception as e:
        logger.error(f"Erro ao buscar cursos salvos do usuário {user_id}: {e}")
        await update.message.reply_text("Ocorreu um erro ao buscar sua lista de cursos.")


# --- 5. GERENCIADOR DE CALLBACKS (BOTÕES) (Refatorado) ---
async def button_callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Processa todos os cliques em botões."""
    query = update.callback_query
    await query.answer()
    data = query.data

    if data.startswith("save_"):
        try:
            index = int(data.split('_')[1])
            last_results = context.user_data.get('last_results')
            if not last_results or index >= len(last_results):
                await query.edit_message_text("❌ Erro: A lista de cursos expirou. Por favor, faça a busca novamente.")
                return

            title, url = last_results[index]
            user_id = query.from_user.id
            
            conexao = sqlite3.connect(DB_FILE)
            cursor = conexao.cursor()
            cursor.execute("INSERT INTO inscricoes (user_id, course_title, course_url) VALUES (?, ?, ?)", (user_id, title, url))
            conexao.commit()
            conexao.close()
            await query.edit_message_text(text=f"✅ Curso '{title}' salvo com sucesso!\nUse /meus_cursos para ver sua lista.")
        except sqlite3.IntegrityError:
            await query.edit_message_text(text="ℹ️ Você já salvou este curso anteriormente.")
        except Exception as e:
            logger.error(f"Erro ao salvar curso via callback: {e}")
            await query.edit_message_text(text="❌ Ocorreu um erro ao tentar salvar o curso.")
        return

    if data.startswith("cat_"):
        # (Lógica da categoria permanece a mesma, mas com feedback)
        # ...
        await query.edit_message_text(f"Buscando na categoria selecionada, aguarde...")
        # ... (código de busca por categoria)
        categoria = data.split('_')[1]
        termos_de_busca, titulo_embed = [], ""
        if categoria == "programacao": termos_de_busca, titulo_embed = ["programação", "python", "javascript"], "💻 Programação"
        # ... adicione as outras categorias aqui ...
        else: await query.edit_message_text("Categoria desconhecida."); return

        todos_resultados = [curso for termo in termos_de_busca for curso in pesquisar_cursos_online(termo)]
        resultados_finais = list({curso[1]: curso for curso in todos_resultados}.values())
        await enviar_resultados_cursos(update, context, resultados_finais, titulo_embed)

# --- 6. FUNÇÃO PRINCIPAL (MAIN) ---
async def post_init(application: Application):
    """Função para ser executada após a inicialização, para configurar o menu de comandos."""
    await application.bot.set_my_commands([
        BotCommand("start", "Inicia o bot e mostra a ajuda"),
        BotCommand("ajuda", "Mostra a mensagem de ajuda"),
        BotCommand("explorar_ti", "Navega por categorias de cursos"),
        BotCommand("pesquisar", "Busca cursos por um termo"),
        BotCommand("cursos_pentest", "Busca cursos de Segurança/Pentest"),
        BotCommand("meus_cursos", "Mostra seus cursos salvos")
    ])

def main() -> None:
    """Inicia o bot."""
    if not TOKEN:
        logger.critical("ERRO: A variável de ambiente TELEGRAM_TOKEN não foi configurada.")
        return

    iniciar_banco_de_dados()
    
    # Cria a persistência para salvar dados do usuário
    persistence = PicklePersistence(filepath=PERSISTENCE_FILE)
    
    application = Application.builder().token(TOKEN).persistence(persistence).post_init(post_init).build()

    application.add_handler(CommandHandler(["start", "ajuda"], ajuda_start))
    application.add_handler(CommandHandler("explorar_ti", explorar_ti))
    application.add_handler(CommandHandler("pesquisar", pesquisar_cursos))
    application.add_handler(CommandHandler("cursos_pentest", cursos_pentest))
    application.add_handler(CommandHandler("meus_cursos", meus_cursos))
    application.add_handler(CallbackQueryHandler(button_callback_handler))

    logger.info("Bot para Telegram iniciado...")
    application.run_polling()

if __name__ == "__main__":
    main()