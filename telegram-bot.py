
import os
import sqlite3
import requests
from bs4 import BeautifulSoup
import urllib.parse
import logging
from typing import List, Tuple

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, BotCommand
# NOVO: Importa BotCommand para definir a lista de comandos
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
from telegram.constants import ParseMode

# --- CONFIGURAÇÕES ---
TOKEN = os.getenv("")

# --- ARQUIVOS DE DADOS ---
DB_FILE = "cursos_usuarios.db"

# --- CONFIGURAÇÃO DE LOGS ---
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)


# --- BANCO DE DADOS ---
def iniciar_banco_de_dados():
    """Cria a tabela do banco de dados se ela não existir."""
    conexao = sqlite3.connect(DB_FILE)
    cursor = conexao.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS inscricoes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            course_title TEXT NOT NULL,
            course_url TEXT NOT NULL,
            UNIQUE(user_id, course_url)
        )
    ''')
    conexao.commit()
    conexao.close()


# --- WEB SCRAPING E BUSCAS (Sem alterações) ---
def pegar_cursos(url: str, base_url: str, filter_keyword: str) -> List[Tuple[str, str]]:
    cursos = []
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3'}
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")
        for a in soup.find_all("a", href=True):
            if filter_keyword in a['href']:
                link = a['href']
                if not link.startswith("http"):
                    link = base_url + link
                title = a.get_text(strip=True) or (a.find('img') and a.find('img').get('alt'))
                if not title or len(title) < 5:
                    title = link.split('/')[-1].split('?')[0].replace('-', ' ').replace('_', ' ').title()
                cursos.append((title.strip(), link))
        return list(dict.fromkeys(cursos))
    except requests.RequestException as e:
        logger.error(f"Erro de rede ao acessar {url}: {e}")
        return []
    except Exception as e:
        logger.error(f"Erro desconhecido ao processar {url}: {e}")
        return []

sites_de_busca = {
    "Udemy (Grátis)": ("https://www.udemy.com/courses/search/?price=price-free&q={}&sort=relevance", "https://www.udemy.com", "/course/"),
    "Coursera": ("https://www.coursera.org/search?query={}", "https://www.coursera.org", "/learn/"),
    "edX": ("https://www.edx.org/search?q={}", "https://www.edx.org", "/course/"),
    "Digital Innovation One": ("https://www.dio.me/browse?search={}", "https://www.dio.me", "/curso/"),
    "Fund. Bradesco Escola Virtual": ("https://www.ev.org.br/catalogo-de-cursos?query={}", "https://www.ev.org.br", "/curso/"),
    "Udacity (Grátis)": ("https://www.udacity.com/courses/all?price=Free&search={}", "https://www.udacity.com", "/course/"),
    "FutureLearn": ("https://www.futurelearn.com/search?q={}", "https://www.futurelearn.com", "/courses/"),
    "Alison (TI)": ("https://alison.com/courses?query={}&category=it", "https://alison.com", "/course/"),
}

def pesquisar_cursos_online(termo: str) -> List[Tuple[str, str]]:
    todos_cursos = []
    termo_formatado = urllib.parse.quote_plus(termo)
    for nome, (url_template, base, filtro) in sites_de_busca.items():
        url_de_busca = url_template.format(termo_formatado)
        logger.info(f"Pesquisando '{termo}' em {nome}...")
        todos_cursos.extend(pegar_cursos(url_de_busca, base, filtro))
    return list(dict.fromkeys(todos_cursos))

sites_pentest = {
    "HackerSec (Grátis)": ("https://hackersec.com/cursos-gratuitos/", "https://hackersec.com", "/curso/"),
    "Cybrary (Free Courses)": ("https://www.cybrary.it/catalog/free/", "https://www.cybrary.it", "/course/"),
}

def pesquisar_cursos_pentest_especializados() -> List[Tuple[str, str]]:
    todos_cursos = []
    for nome, (url_fixa, base, filtro) in sites_pentest.items():
        logger.info(f"Pesquisando em site especializado: {nome}...")
        todos_cursos.extend(pegar_cursos(url_fixa, base, filtro))
    return list(dict.fromkeys(todos_cursos))


# --- FUNÇÕES AUXILIARES DO TELEGRAM (Sem alterações) ---
def get_sanitized_text(text: str) -> str:
    escape_chars = r'_*[]()~`>#+-=|{}.!'
    return ''.join(f'\\{char}' if char in escape_chars else char for char in text)

async def enviar_resultados_cursos(update: Update, context: ContextTypes.DEFAULT_TYPE, cursos: List[Tuple[str, str]], titulo_header: str):
    chat_id = update.effective_chat.id
    if not cursos:
        await context.bot.send_message(chat_id=chat_id, text=f"Nenhum curso encontrado para '{titulo_header}'.")
        return
    await context.bot.send_message(
        chat_id=chat_id, 
        text=f"🔎 *Resultados para '{get_sanitized_text(titulo_header)}'*", 
        parse_mode=ParseMode.MARKDOWN_V2
    )
    for titulo, url in cursos[:10]:
        url_hash = str(hash(url))
        context.user_data[url_hash] = {'title': titulo, 'url': url}
        keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("✅ Salvar na minha lista", callback_data=f"save:{url_hash}")]])
        titulo_curto = (titulo[:75] + '...') if len(titulo) > 75 else titulo
        mensagem_curso = f"🎓 *{get_sanitized_text(titulo_curto)}*\n\n[Acessar Curso]({url})"
        await context.bot.send_message(
            chat_id=chat_id, text=mensagem_curso, reply_markup=keyboard,
            parse_mode=ParseMode.MARKDOWN_V2, disable_web_page_preview=True
        )


# --- COMANDOS DO BOT (HANDLERS) (Sem alterações) ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    await update.message.reply_html(
        f"Olá, {user.mention_html()}!\n\n"
        "Eu sou seu assistente para encontrar cursos de TI. "
        "Use o menu de comandos (botão ` / `) para começar."
    )

async def ajuda(update: Update, context: ContextTypes.DEFAULT_TYPE):
    texto_ajuda = (
        "🤖 *Ajuda do Bot de Cursos de TI*\n\n"
        "Olá\\! Eu sou seu assistente para encontrar cursos de Tecnologia da Informação em diversas plataformas online\\.\n\n"
        "Veja abaixo como usar meus comandos:\n\n"
        "*/explorar_ti*\n"
        "Abre um menu interativo para você escolher uma área de TI \\(Programação, Redes, Cloud, etc\\.\\) e ver os cursos disponíveis\\.\n\n"
        "*/pesquisar_cursos* `termo`\n"
        "Busca diretamente por um assunto específico\\.\n"
        "\\*Exemplo:* `/pesquisar_cursos Python`\n\n"
        "*/cursos_pentest*\n"
        "Realiza uma busca focada em cursos de Segurança da Informação, Pentest e Hacking Ético\\.\n\n"
        "*/meus_cursos*\n"
        "Mostra a sua lista pessoal de cursos que você salvou usando o botão ✅\\.\n"
    )
    await update.message.reply_markdown_v2(texto_ajuda)

async def explorar_ti(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("💻 Programação", callback_data='cat_programacao'), InlineKeyboardButton("🌐 Redes e Infra", callback_data='cat_redes')],
        [InlineKeyboardButton("☁️ Cloud Computing", callback_data='cat_cloud'), InlineKeyboardButton("🛡️ Segurança", callback_data='cat_seguranca')],
        [InlineKeyboardButton("🗄️ Banco de Dados", callback_data='cat_dados'), InlineKeyboardButton("📊 Ciência de Dados", callback_data='cat_ciencia_dados')],
        [InlineKeyboardButton("⚙️ DevOps", callback_data='cat_devops')],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("Olá! Escolha uma área de TI abaixo para que eu possa encontrar os melhores cursos para você:", reply_markup=reply_markup)

async def pesquisar_cursos(update: Update, context: ContextTypes.DEFAULT_TYPE):
    termo_busca = " ".join(context.args)
    if not termo_busca:
        await update.message.reply_text("Por favor, me diga o que você quer aprender.\nExemplo: `/pesquisar_cursos Python`")
        return
    await update.message.reply_text(f"Buscando cursos sobre '{termo_busca}', por favor aguarde...")
    resultados = pesquisar_cursos_online(termo_busca)
    await enviar_resultados_cursos(update, context, resultados, termo_busca)
    
async def cursos_pentest(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Buscando cursos de Pentest e Hacking Ético, aguarde...")
    todos_resultados = pesquisar_cursos_pentest_especializados() + pesquisar_cursos_online("pentest") + pesquisar_cursos_online("ethical hacking")
    await enviar_resultados_cursos(update, context, list(dict.fromkeys(todos_resultados)), "Pentest & Hacking Ético")

async def meus_cursos(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    try:
        conexao = sqlite3.connect(DB_FILE)
        cursor = conexao.cursor()
        cursor.execute("SELECT course_title, course_url FROM inscricoes WHERE user_id = ?", (user_id,))
        cursos_do_usuario = cursor.fetchall()
        conexao.close()
    except Exception as e:
        logger.error(f"Erro ao buscar cursos do usuário no DB: {e}")
        await update.message.reply_text("Ocorreu um erro ao buscar sua lista de cursos.")
        return
    if not cursos_do_usuario:
        await update.message.reply_text("Você ainda não salvou nenhum curso. Use os botões ✅ para adicioná-los à sua lista!")
        return
    lista_formatada = ""
    for i, (titulo, url) in enumerate(cursos_do_usuario[:25], 1):
        titulo_curto = (titulo[:70] + '...') if len(titulo) > 70 else titulo
        lista_formatada += f"{i}\\. *[{get_sanitized_text(titulo_curto)}]({url})*\n"
    mensagem_final = f"📚 *Meus Cursos Salvos*\n\nSua lista de cursos, {update.effective_user.mention_markdown_v2()}\\.\n\n{lista_formatada}"
    await update.message.reply_markdown_v2(mensagem_final, disable_web_page_preview=True)


# --- GERENCIADOR DE CALLBACKS (BOTÕES) (Sem alterações) ---
async def button_callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    if data.startswith("save:"):
        url_hash = data.split(":", 1)[1]
        if url_hash not in context.user_data:
            await query.edit_message_text(text=query.message.text + "\n\n❌ Erro: Os dados deste curso expiraram. Por favor, faça a busca novamente.")
            return
        curso_info = context.user_data[url_hash]
        user_id = query.from_user.id
        course_title, course_url = curso_info['title'], curso_info['url']
        try:
            conexao = sqlite3.connect(DB_FILE)
            cursor = conexao.cursor()
            cursor.execute("INSERT INTO inscricoes (user_id, course_title, course_url) VALUES (?, ?, ?)", (user_id, course_title, course_url))
            conexao.commit()
            conexao.close()
            await query.edit_message_text(text=query.message.text_markdown_v2 + "\n\n*Curso salvo na sua lista\\!*", parse_mode=ParseMode.MARKDOWN_V2, disable_web_page_preview=True)
            await context.bot.answer_callback_query(callback_query_id=query.id, text="Curso salvo!", show_alert=False)
        except sqlite3.IntegrityError:
            await context.bot.answer_callback_query(callback_query_id=query.id, text="Você já salvou este curso!", show_alert=True)
        except Exception as e:
            logger.error(f"Erro de DB ao salvar curso: {e}")
            await context.bot.answer_callback_query(callback_query_id=query.id, text="Erro ao tentar salvar o curso.", show_alert=True)
    elif data.startswith("cat_"):
        categoria = data.split("_", 1)[1]
        mapa_categorias = {
            "programacao": (["programação", "python", "javascript", "java"], "💻 Cursos de Programação"),
            "redes": (["redes de computadores", "ccna", "infraestrutura ti"], "🌐 Cursos de Redes e Infraestrutura"),
            "cloud": (["aws", "azure", "google cloud"], "☁️ Cursos de Cloud Computing"),
            "dados": (["sql", "banco de dados", "nosql"], "🗄️ Cursos de Banco de Dados"),
            "ciencia_dados": (["ciencia de dados", "machine learning", "inteligencia artificial"], "📊 Cursos de Ciência de Dados"),
            "devops": (["devops", "docker", "kubernetes", "ci/cd"], "⚙️ Cursos de DevOps"),
        }
        if categoria == "seguranca":
            await query.edit_message_text(text="Buscando cursos de Segurança, por favor aguarde...")
            await cursos_pentest(update, context)
            return
        if categoria in mapa_categorias:
            termos_de_busca, titulo_header = mapa_categorias[categoria]
            await query.edit_message_text(text=f"Buscando cursos de {titulo_header.split(' ', 1)[1]}, por favor aguarde...")
            todos_resultados = []
            for termo in termos_de_busca:
                todos_resultados.extend(pesquisar_cursos_online(termo))
            await enviar_resultados_cursos(update, context, list(dict.fromkeys(todos_resultados)), titulo_header)


# NOVO: Função para configurar os comandos no menu do Telegram
async def post_init(application: Application):
    """Configura a lista de comandos do bot no Telegram após a inicialização."""
    commands = [
        BotCommand("explorar_ti", "Navegue por categorias de cursos de TI"),
        BotCommand("pesquisar_cursos", "Pesquise por um curso específico"),
        BotCommand("cursos_pentest", "Encontre cursos de segurança e pentest"),
        BotCommand("meus_cursos", "Veja sua lista de cursos salvos"),
        BotCommand("ajuda", "Mostra esta mensagem de ajuda"),
    ]
    await application.bot.set_my_commands(commands)
    print("Lista de comandos configurada no Telegram!")


# --- FUNÇÃO PRINCIPAL ---
def main():
    """Função principal que inicia o bot."""
    if not TOKEN:
        print("ERRO CRÍTICO: A variável de ambiente TELEGRAM_TOKEN não foi configurada.")
        return

    iniciar_banco_de_dados()

    # ALTERADO: Adiciona a função post_init ao builder para configurar os comandos na inicialização
    application = Application.builder().token(TOKEN).post_init(post_init).build()

    # Registra todos os handlers (comandos, botões, etc.)
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("ajuda", ajuda))
    application.add_handler(CommandHandler("explorar_ti", explorar_ti))
    application.add_handler(CommandHandler("pesquisar_cursos", pesquisar_cursos))
    application.add_handler(CommandHandler("cursos_pentest", cursos_pentest))
    application.add_handler(CommandHandler("meus_cursos", meus_cursos))
    application.add_handler(CallbackQueryHandler(button_callback_handler))

    print("Bot do Telegram iniciado. Pressione Ctrl+C para parar.")
    application.run_polling()


if __name__ == '__main__':
    main()