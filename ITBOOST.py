import discord
from discord.ext import commands
from discord import app_commands
import os
import sqlite3
import asyncio
import aiohttp
from bs4 import BeautifulSoup
import urllib.parse
from typing import List, Literal

# --- CONFIGURAÇÕES ---
TOKEN = os.getenv("DISCORD_TOKEN", "")
DB_FILE = "cursos_usuarios.db"
CourseType = Literal["free", "paid", "all"]

# --- LISTA DE SITES E CATEGORIAS (Internalizada) ---
SITES_DE_BUSCA = {
    "Udemy": {"url": "https://www.udemy.com/courses/search/?q={}&sort=relevance", "base": "https://www.udemy.com", "filter": "/course/", "type": "mixed"},
    "Coursera": {"url": "https://www.coursera.org/search?query={}", "base": "https://www.coursera.org", "filter": "/learn/", "type": "mixed"},
    "edX": {"url": "https://www.edx.org/search?q={}", "base": "https://www.edx.org", "filter": "/course/", "type": "mixed"},
    "Digital Innovation One": {"url": "https://www.dio.me/browse?search={}", "base": "https://www.dio.me", "filter": "/curso/", "type": "free"},
    "Fund. Bradesco Escola Virtual": {"url": "https://www.ev.org.br/catalogo-de-cursos?query={}", "base": "https://www.ev.org.br", "filter": "/curso/", "type": "free"},
    "Udacity": {"url": "https://www.udacity.com/courses/all?search={}", "base": "https://www.udacity.com", "filter": "/course/", "type": "mixed"},
    "Alison": {"url": "https://alison.com/courses?query={}&category=it", "base": "https://alison.com", "filter": "/course/", "type": "free"},
    "Khan Academy": {"url": "https://www.khanacademy.org/search?page_search_query={}", "base": "https://www.khanacademy.org", "filter": "/x/", "type": "free"},
    "freeCodeCamp": {"url": "https://www.freecodecamp.org/news/search?query={}", "base": "https://www.freecodecamp.org/news", "filter": "/", "type": "free"},
    "Alura": {"url": "https://www.alura.com.br/busca?query={}", "base": "https://www.alura.com.br", "filter": "/curso/", "type": "paid"},
    "DataCamp": {"url": "https://www.datacamp.com/search?q={}", "base": "https://www.datacamp.com", "filter": "/courses/", "type": "paid"},
    "Pluralsight": {"url": "https://www.pluralsight.com/search?q={}", "base": "https://www.pluralsight.com", "filter": "/courses/", "type": "paid"},
    "Class Central": {"url": "https://www.classcentral.com/search?q={}", "base": "https://www.classcentral.com", "filter": "/course/", "type": "mixed"},
}
SITES_PENTEST = {
    "HackerSec": {"url": "https://hackersec.com/cursos-gratuitos/", "base": "https://hackersec.com", "filter": "/curso/", "type": "free"},
    "Cybrary": {"url": "https://www.cybrary.it/catalog/all/", "base": "https://www.cybrary.it", "filter": "/course/", "type": "mixed"},
    "Hack The Box Academy": {"url": "https://academy.hackthebox.com/catalogue", "base": "https://academy.hackthebox.com", "filter": "/module/", "type": "mixed"},
}
MAPA_CATEGORIAS = {
    "programacao": (["programação", "python", "javascript", "java"], "💻 Cursos de Programação"),
    "redes": (["redes de computadores", "ccna", "infraestrutura"], "🌐 Cursos de Redes"),
    "cloud": (["aws", "azure", "google cloud"], "☁️ Cursos de Cloud"),
    "seguranca": (["segurança da informação", "pentest", "hacking etico"], "🛡️ Cursos de Segurança"),
    "dados": (["sql", "banco de dados", "nosql"], "🗄️ Cursos de Banco de Dados"),
    "ciencia_dados": (["ciencia de dados", "machine learning", "ia"], "📊 Cursos de Ciência de Dados"),
    "devops": (["devops", "docker", "kubernetes"], "⚙️ Cursos de DevOps"),
}

# --- CONFIGURAÇÃO DO BOT ---
intents = discord.Intents.default()
bot = commands.Bot(command_prefix="!", intents=intents)

# --- WEB SCRAPING OTIMIZADO (Async) ---
async def _fetch_page(session: aiohttp.ClientSession, url: str) -> str:
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
    try:
        async with session.get(url, headers=headers, timeout=15) as response:
            response.raise_for_status()
            return await response.text()
    except Exception:
        return ""

def _parse_courses(html: str, base_url: str, filter_keyword: str) -> List[tuple[str, str]]:
    cursos = []
    soup = BeautifulSoup(html, "html.parser")
    for a in soup.find_all("a", href=True):
        href = a['href']
        if filter_keyword in href:
            link = href if href.startswith("http") else urllib.parse.urljoin(base_url, href)
            title = a.get_text(strip=True) or (a.find('img') and a.find('img').get('alt', '').strip())
            if not title or len(title) < 5:
                title = link.split('/')[-1].split('?')[0].replace('-', ' ').replace('_', ' ').title()
            if title:
                cursos.append((title.strip(), link))
    return list(dict.fromkeys(cursos))

async def _scrape_site(session: aiohttp.ClientSession, url_template: str, base_url: str, filter_keyword: str) -> List[tuple[str, str]]:
    html = await _fetch_page(session, url_template)
    if html:
        return _parse_courses(html, base_url, filter_keyword)
    return []

async def pesquisar_cursos_online(termo: str, course_type: CourseType = "all") -> List[tuple[str, str]]:
    termo_formatado = urllib.parse.quote_plus(termo)
    sites_filtrados = {
        name: data for name, data in SITES_DE_BUSCA.items()
        if course_type == "all" or data['type'] == course_type or data['type'] == 'mixed'
    }
    async with aiohttp.ClientSession() as session:
        tasks = [
            _scrape_site(session, data['url'].format(termo_formatado), data['base'], data['filter'])
            for data in sites_filtrados.values()
        ]
        resultados_por_site = await asyncio.gather(*tasks)
    return [curso for sublist in resultados_por_site for curso in sublist]

async def pesquisar_cursos_pentest(course_type: CourseType = "all") -> List[tuple[str, str]]:
    sites_filtrados = {
        name: data for name, data in SITES_PENTEST.items()
        if course_type == "all" or data['type'] == course_type or data['type'] == 'mixed'
    }
    async with aiohttp.ClientSession() as session:
        tasks = [
            _scrape_site(session, data['url'].format(''), data['base'], data['filter'])
            for data in sites_filtrados.values()
        ]
        resultados_por_site = await asyncio.gather(*tasks)
    return [curso for sublist in resultados_por_site for curso in sublist]


# --- BANCO DE DADOS ---
def iniciar_banco_de_dados():
    with sqlite3.connect(DB_FILE) as conexao:
        cursor = conexao.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS inscricoes (
                id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL,
                course_title TEXT NOT NULL, course_url TEXT NOT NULL,
                UNIQUE(user_id, course_url)
            )
        ''')

# --- COMPONENTES DE UI (VIEWS E BOTÕES) ---
class CursoView(discord.ui.View):
    def __init__(self, course_title: str, course_url: str):
        super().__init__(timeout=None)
        self.course_title = course_title
        self.course_url = course_url

    @discord.ui.button(label="✅ Salvar na minha lista", style=discord.ButtonStyle.success)
    async def inscrever_button_callback(self, interaction: discord.Interaction, button: discord.ui.Button):
        user_id = interaction.user.id
        try:
            with sqlite3.connect(DB_FILE) as conexao:
                cursor = conexao.cursor()
                cursor.execute("INSERT INTO inscricoes (user_id, course_title, course_url) VALUES (?, ?, ?)",
                               (user_id, self.course_title, self.course_url))
            await interaction.response.send_message(f"Você salvou o curso: '{self.course_title}'!", ephemeral=True)
        except sqlite3.IntegrityError:
            await interaction.response.send_message("Você já salvou este curso!", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message("Ocorreu um erro ao salvar.", ephemeral=True)

class CategoriaSelect(discord.ui.Select):
    def __init__(self, course_type: CourseType):
        self.course_type = course_type
        options = [
            discord.SelectOption(label="Programação", emoji="💻", value="programacao"),
            discord.SelectOption(label="Redes", emoji="🌐", value="redes"),
            discord.SelectOption(label="Cloud", emoji="☁️", value="cloud"),
            discord.SelectOption(label="Segurança", emoji="🛡️", value="seguranca"),
            discord.SelectOption(label="Banco de Dados", emoji="🗄️", value="dados"),
            discord.SelectOption(label="Ciência de Dados", emoji="📊", value="ciencia_dados"),
            discord.SelectOption(label="DevOps", emoji="⚙️", value="devops"),
        ]
        super().__init__(placeholder="Escolha uma área de TI para explorar...", options=options)

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer(thinking=True, ephemeral=True)
        categoria_key = self.values[0]
        termos_de_busca, titulo_header_base = MAPA_CATEGORIAS[categoria_key]
        
        tipo_texto = "Pagos" if self.course_type == "paid" else "Gratuitos"
        titulo_header = f"{titulo_header_base} ({tipo_texto})"

        tasks = []
        if categoria_key == "seguranca":
            tasks.append(pesquisar_cursos_pentest(course_type=self.course_type))

        for termo in termos_de_busca:
            tasks.append(pesquisar_cursos_online(termo, course_type=self.course_type))

        resultados_listas = await asyncio.gather(*tasks)
        resultados_finais = list(dict.fromkeys([item for sublist in resultados_listas for item in sublist]))

        await _enviar_resultados_para_discord(interaction, resultados_finais, titulo_header)

class CategoriaTIView(discord.ui.View):
    def __init__(self, course_type: CourseType):
        super().__init__(timeout=None)
        self.add_item(CategoriaSelect(course_type))

async def _enviar_resultados_para_discord(interaction: discord.Interaction, cursos: List, titulo_header: str):
    if not cursos:
        await interaction.followup.send(f"Nenhum curso encontrado para '{titulo_header}'.", ephemeral=True)
        return

    resultados_limitados = cursos[:10]
    lista_formatada = "\n".join(f"{i}. **[{c[0][:75]}]({c[1]})**" for i, c in enumerate(resultados_limitados, 1))

    embed = discord.Embed(title=titulo_header, description=lista_formatada, color=discord.Color.blue())
    embed.set_footer(text=f"Mostrando {len(resultados_limitados)} de {len(cursos)} resultados.")
    await interaction.followup.send(embed=embed, ephemeral=True)

    for titulo, url in resultados_limitados:
        embed_curso = discord.Embed(title=titulo, url=url, description="Clique abaixo para salvar este curso.", color=discord.Color.blue())
        view_curso = CursoView(course_title=titulo, course_url=url)
        await interaction.followup.send(embed=embed_curso, view=view_curso, ephemeral=True)

# --- COMANDOS DO BOT ---
@bot.event
async def on_ready():
    print(f'Bot conectado como {bot.user}')
    iniciar_banco_de_dados()
    bot.add_view(CursoView(course_title="", course_url=""))
    try:
        synced = await bot.tree.sync()
        print(f"Sincronizados {len(synced)} comandos.")
    except Exception as e:
        print(f"Erro ao sincronizar comandos: {e}")

@bot.tree.command(name="cursos_gratuitos", description="Encontre cursos de TI em plataformas gratuitas.")
async def cursos_gratuitos(interaction: discord.Interaction):
    view = CategoriaTIView(course_type="free")
    await interaction.response.send_message("Escolha uma área para explorar cursos gratuitos:", view=view, ephemeral=True)

@bot.tree.command(name="cursos_pagos", description="Encontre cursos de TI em plataformas pagas.")
async def cursos_pagos(interaction: discord.Interaction):
    view = CategoriaTIView(course_type="paid")
    await interaction.response.send_message("Escolha uma área para explorar cursos pagos:", view=view, ephemeral=True)

@bot.tree.command(name="pesquisar_cursos", description="Pesquisa por um termo em TODAS as plataformas.")
@app_commands.describe(termo="O que você quer aprender?")
async def pesquisar_cursos(interaction: discord.Interaction, termo: str):
    await interaction.response.defer(thinking=True, ephemeral=True)
    resultados = await pesquisar_cursos_online(termo, course_type="all")
    await _enviar_resultados_para_discord(interaction, resultados, f"🔎 Resultados da Busca por '{termo}'")

@bot.tree.command(name="ajuda", description="Exibe informações de ajuda sobre como usar o bot.")
async def ajuda(interaction: discord.Interaction):
    embed = discord.Embed(
        title="🤖 Ajuda do Bot de Cursos de TI",
        description="Eu sou seu assistente para encontrar cursos de TI. Veja como me usar:",
        color=discord.Color.purple()
    )
    embed.add_field(name="`/cursos_gratuitos`", value="Abre um menu de categorias para buscar cursos gratuitos.", inline=False)
    embed.add_field(name="`/cursos_pagos`", value="Abre um menu de categorias para buscar cursos pagos.", inline=False)
    embed.add_field(name="`/pesquisar_cursos [termo]`", value="Busca por um assunto em TODAS as plataformas.\n*Exemplo: `/pesquisar_cursos termo:Python`*", inline=False)
    embed.add_field(name="`/meus_cursos`", value="Mostra a sua lista de cursos salvos.", inline=False)
    embed.set_footer(text="Espero que ajude você a encontrar o curso perfeito!")
    await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.tree.command(name="meus_cursos", description="Mostra sua lista de cursos salvos.")
async def meus_cursos(interaction: discord.Interaction):
    with sqlite3.connect(DB_FILE) as con:
        cursos = con.execute("SELECT course_title, course_url FROM inscricoes WHERE user_id = ?", (interaction.user.id,)).fetchall()
    if not cursos:
        await interaction.response.send_message("Você não tem cursos salvos.", ephemeral=True)
        return
    lista = "\n".join(f"{i}. **[{c[0][:70]}]({c[1]})**" for i, c in enumerate(cursos[:25], 1))
    embed = discord.Embed(title="📚 Meus Cursos Salvos", description=lista, color=discord.Color.green())
    await interaction.response.send_message(embed=embed, ephemeral=True)

# --- INICIA O BOT ---
if not TOKEN:
    print("ERRO CRÍTICO: DISCORD_TOKEN não configurado!")
else:
    bot.run(TOKEN)