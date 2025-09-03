import discord
from discord.ext import commands, tasks
from discord import app_commands
import requests
from bs4 import BeautifulSoup
import os
import sqlite3
import urllib.parse
from typing import List

# --- CONFIGURAÇÕES ---
TOKEN = os.getenv("DISCORD_TOKEN", "")
# GUILD_ID e CHANNEL_ID foram removidos para o bot ser global

# --- ARQUIVOS DE DADOS ---
DB_FILE = "cursos_usuarios.db"
LINKS_ENVIADOS_FILE = "links_enviados.txt"

# --- CONFIGURAÇÃO DO BOT ---
intents = discord.Intents.default()
bot = commands.Bot(command_prefix="!", intents=intents)

# --- BANCO DE DADOS (Sem alterações) ---
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

# --- VIEW COM BOTÃO (Sem alterações) ---
class CursoView(discord.ui.View):
    def __init__(self, course_title: str, course_url: str):
        super().__init__(timeout=None)
        self.course_title = course_title
        self.course_url = course_url

    @discord.ui.button(label="✅ Salvar na minha lista", style=discord.ButtonStyle.success, custom_id="inscrever_button")
    async def inscrever_button_callback(self, interaction: discord.Interaction, button: discord.ui.Button):
        user_id = interaction.user.id
        try:
            conexao = sqlite3.connect(DB_FILE)
            cursor = conexao.cursor()
            cursor.execute("INSERT INTO inscricoes (user_id, course_title, course_url) VALUES (?, ?, ?)",
                           (user_id, self.course_title, self.course_url))
            conexao.commit()
            conexao.close()
            await interaction.response.send_message(f"Você salvou o curso: '{self.course_title}'! Use `/meus_cursos` para ver sua lista.", ephemeral=True)
        except sqlite3.IntegrityError:
            await interaction.response.send_message("Você já salvou este curso na sua lista!", ephemeral=True)
        except Exception as e:
            print(f"Erro no banco de dados: {e}")
            await interaction.response.send_message("Ocorreu um erro ao tentar salvar o curso.", ephemeral=True)


# --- COMPONENTES DO MENU DE SELEÇÃO (Sem alterações) ---
class CategoriaSelect(discord.ui.Select):
    def __init__(self):
        options = [
            discord.SelectOption(label="Programação", description="Python, Java, JavaScript, C#, etc.", emoji="💻", value="programacao"),
            discord.SelectOption(label="Redes e Infraestrutura", description="Redes de Computadores, CCNA, Servidores.", emoji="🌐", value="redes"),
            discord.SelectOption(label="Cloud Computing", description="AWS, Azure, Google Cloud.", emoji="☁️", value="cloud"),
            discord.SelectOption(label="Segurança da Informação", description="Pentest, Hacking Ético, Segurança Ofensiva.", emoji="🛡️", value="seguranca"),
            discord.SelectOption(label="Banco de Dados", description="SQL, NoSQL, Modelagem de Dados.", emoji="🗄️", value="dados"),
            discord.SelectOption(label="Ciência de Dados", description="Machine Learning, Análise de Dados, IA.", emoji="📊", value="ciencia_dados"),
            discord.SelectOption(label="DevOps", description="Integração Contínua, Docker, Kubernetes.", emoji="⚙️", value="devops"),
        ]
        super().__init__(placeholder="Escolha uma área de TI para explorar...", min_values=1, max_values=1, options=options, custom_id="menu_selecao_categoria")

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer(thinking=True, ephemeral=True)
        categoria_escolhida = self.values[0]
        termos_de_busca: List[str] = []
        titulo_embed = ""
        # ... (lógica do callback permanece a mesma) ...
        if categoria_escolhida == "programacao":
            termos_de_busca = ["programação", "python", "javascript", "java"]
            titulo_embed = "💻 Cursos de Programação"
        elif categoria_escolhida == "redes":
            termos_de_busca = ["redes de computadores", "ccna", "infraestrutura ti"]
            titulo_embed = "🌐 Cursos de Redes e Infraestrutura"
        elif categoria_escolhida == "cloud":
            termos_de_busca = ["aws", "azure", "google cloud"]
            titulo_embed = "☁️ Cursos de Cloud Computing"
        elif categoria_escolhida == "seguranca":
            resultados_especializados = pesquisar_cursos_pentest_especializados()
            resultados_gerais = pesquisar_cursos_online("segurança da informação")
            todos_resultados = resultados_especializados + resultados_gerais
            titulo_embed = "🛡️ Cursos de Segurança da Informação"
        elif categoria_escolhida == "dados":
            termos_de_busca = ["sql", "banco de dados", "nosql"]
            titulo_embed = "🗄️ Cursos de Banco de Dados"
        elif categoria_escolhida == "ciencia_dados":
            termos_de_busca = ["ciencia de dados", "machine learning", "inteligencia artificial"]
            titulo_embed = "📊 Cursos de Ciência de Dados"
        elif categoria_escolhida == "devops":
            termos_de_busca = ["devops", "docker", "kubernetes", "ci/cd"]
            titulo_embed = "⚙️ Cursos de DevOps"

        if categoria_escolhida != "seguranca":
            todos_resultados = []
            for termo in termos_de_busca:
                todos_resultados.extend(pesquisar_cursos_online(termo))
        
        resultados_finais = list({curso[1]: curso for curso in todos_resultados}.values())

        if not resultados_finais:
            await interaction.followup.send(f"Nenhum curso encontrado para a categoria '{titulo_embed}'.", ephemeral=True)
            return

        resultados_limitados = resultados_finais[:10]
        lista_formatada = ""
        for i, (titulo, url) in enumerate(resultados_limitados, 1):
            titulo_curto = (titulo[:75] + '...') if len(titulo) > 75 else titulo
            lista_formatada += f"{i}. **[{titulo_curto}]({url})**\n"
        embed = discord.Embed(title=titulo_embed, description=lista_formatada, color=discord.Color.blue())
        embed.set_footer(text=f"Mostrando {len(resultados_limitados)} de {len(resultados_finais)} resultados.")
        await interaction.followup.send(embed=embed, ephemeral=True)
        for titulo, url in resultados_limitados:
            embed_curso = discord.Embed(title=titulo, url=url, description="Clique no botão abaixo para salvar este curso na sua lista pessoal.", color=discord.Color.blue())
            view_curso = CursoView(course_title=titulo, course_url=url)
            await interaction.followup.send(embed=embed_curso, view=view_curso, ephemeral=True)

class CategoriaTIView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(CategoriaSelect())

# --- WEB SCRAPING E BUSCAS (Sem alterações) ---
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
                title = a.get_text(strip=True)
                if not title:
                    img_tag = a.find('img')
                    if img_tag and img_tag.get('alt'):
                        title = img_tag['alt']
                if not title or len(title) < 5:
                    title = link.split('/')[-1].split('?')[0].replace('-', ' ').replace('_', ' ').title()
                cursos.append((title.strip(), link))
        return list({curso[1]: curso for curso in cursos}.values())
    except requests.RequestException as e:
        print(f"Erro ao acessar {url}: {e}")
        return []
    except Exception as e:
        print(f"Erro desconhecido ao processar {url}: {e}")
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

def pesquisar_cursos_online(termo: str):
    todos_cursos = []
    termo_formatado = urllib.parse.quote_plus(termo)
    for nome, (url_template, base, filtro) in sites_de_busca.items():
        url_de_busca = url_template.format(termo_formatado)
        print(f"Pesquisando '{termo}' em {nome}...")
        cursos_encontrados = pegar_cursos(url_de_busca, base, filtro)
        todos_cursos.extend(cursos_encontrados)
    return list({curso[1]: curso for curso in todos_cursos}.values())

sites_pentest = {
    "HackerSec (Grátis)": ("https://hackersec.com/cursos-gratuitos/", "https://hackersec.com", "/curso/"),
    "Cybrary (Free Courses)": ("https://www.cybrary.it/catalog/free/", "https://www.cybrary.it", "/course/"),
}

def pesquisar_cursos_pentest_especializados():
    todos_cursos = []
    for nome, (url_fixa, base, filtro) in sites_pentest.items():
        cursos_encontrados = pegar_cursos(url_fixa, base, filtro)
        todos_cursos.extend(cursos_encontrados)
    return list({curso[1]: curso for curso in todos_cursos}.values())

# --- COMANDOS DO BOT ---
@bot.event
async def on_ready():
    print(f'Bot conectado como {bot.user}')
    iniciar_banco_de_dados()
    bot.add_view(CursoView(course_title="", course_url="")) 
    bot.add_view(CategoriaTIView())
    try:
        synced = await bot.tree.sync()
        print(f"Sincronizados {len(synced)} comandos globalmente.")
    except Exception as e:
        print(f"Erro ao sincronizar comandos: {e}")

@bot.tree.command(name="explorar_ti", description="Navegue por categorias e encontre cursos de TI.")
async def explorar_ti(interaction: discord.Interaction):
    view = CategoriaTIView()
    await interaction.response.send_message("Olá! Escolha uma área de TI abaixo para que eu possa encontrar os melhores cursos para você:", view=view, ephemeral=True)

@bot.tree.command(name="pesquisar_cursos", description="Pesquisa por cursos de TI em diversas plataformas.")
@app_commands.describe(termo="O que você quer aprender? (Ex: Python, AWS, Big Data, CCNA, Java)")
async def pesquisar_cursos(interaction: discord.Interaction, termo: str):
    await interaction.response.defer(ephemeral=True, thinking=True)
    resultados = pesquisar_cursos_online(termo)
    if not resultados:
        await interaction.followup.send(f"Nenhum curso encontrado para o termo '{termo}'.", ephemeral=True)
        return
    resultados_limitados = resultados[:10]
    lista_formatada = ""
    for i, (titulo, url) in enumerate(resultados_limitados, 1):
        titulo_curto = (titulo[:75] + '...') if len(titulo) > 75 else titulo
        lista_formatada += f"{i}. **[{titulo_curto}]({url})**\n"
    embed = discord.Embed(title=f"🔎 Resultados da Busca por '{termo}'", description=lista_formatada, color=discord.Color.orange())
    embed.set_footer(text=f"Mostrando {len(resultados_limitados)} de {len(resultados)} resultados.")
    await interaction.followup.send(embed=embed, ephemeral=True)
    for titulo, url in resultados_limitados:
        embed_curso = discord.Embed(title=titulo, url=url, description="Clique no botão abaixo para salvar este curso na sua lista pessoal.", color=discord.Color.blue())
        view = CursoView(course_title=titulo, course_url=url)
        await interaction.followup.send(embed=embed_curso, view=view, ephemeral=True)

@bot.tree.command(name="cursos_pentest", description="Busca cursos de Pentest e Hacking Ético.")
async def cursos_pentest(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True, thinking=True)
    resultados_especializados = pesquisar_cursos_pentest_especializados()
    resultados_gerais = pesquisar_cursos_online("pentest")
    resultados_hacking = pesquisar_cursos_online("ethical hacking")
    todos_resultados = resultados_especializados + resultados_gerais + resultados_hacking
    resultados_finais = list({curso[1]: curso for curso in todos_resultados}.values())
    if not resultados_finais:
        await interaction.followup.send("Nenhum curso de Pentest ou Hacking Ético foi encontrado.", ephemeral=True)
        return
    resultados_limitados = resultados_finais[:10]
    lista_formatada = ""
    for i, (titulo, url) in enumerate(resultados_limitados, 1):
        titulo_curto = (titulo[:75] + '...') if len(titulo) > 75 else titulo
        lista_formatada += f"{i}. **[{titulo_curto}]({url})**\n"
    embed = discord.Embed(title="🛡️ Cursos de Pentest & Hacking Ético", description=lista_formatada, color=discord.Color.red())
    embed.set_footer(text=f"Mostrando {len(resultados_limitados)} de {len(resultados_finais)} resultados.")
    await interaction.followup.send(embed=embed, ephemeral=True)
    for titulo, url in resultados_limitados:
        embed_curso = discord.Embed(title=titulo, url=url, description="Clique no botão abaixo para salvar este curso na sua lista pessoal.", color=discord.Color.dark_red())
        view = CursoView(course_title=titulo, course_url=url)
        await interaction.followup.send(embed=embed_curso, view=view, ephemeral=True)

# --- NOVO COMANDO DE AJUDA ---
@bot.tree.command(name="ajuda", description="Exibe informações de ajuda sobre como usar o bot e seus comandos.")
async def ajuda(interaction: discord.Interaction):
    """Mostra uma mensagem de ajuda com todos os comandos disponíveis."""
    
    embed_ajuda = discord.Embed(
        title="🤖 Ajuda do Bot de Cursos de TI",
        description="Olá! Eu sou seu assistente para encontrar cursos de Tecnologia da Informação em diversas plataformas online.\n\nVeja abaixo como usar meus comandos:",
        color=discord.Color.purple() # Uma cor diferente para destacar a ajuda
    )
    
    embed_ajuda.add_field(
        name="`/explorar_ti`", 
        value="Abre um menu interativo para você escolher uma área de TI (Programação, Redes, Cloud, etc.) e ver os cursos disponíveis.", 
        inline=False
    )
    
    embed_ajuda.add_field(
        name="`/pesquisar_cursos [termo]`", 
        value="Busca diretamente por um assunto específico. \n*Exemplo: `/pesquisar_cursos termo:Python`*", 
        inline=False
    )
    
    embed_ajuda.add_field(
        name="`/cursos_pentest`", 
        value="Realiza uma busca focada em cursos de Segurança da Informação, Pentest e Hacking Ético.", 
        inline=False
    )
    
    embed_ajuda.add_field(
        name="`/meus_cursos`", 
        value="Mostra a sua lista pessoal de cursos que você salvou usando o botão.", 
        inline=False
    )
    
    embed_ajuda.add_field(
        name="✅ Botão 'Salvar na minha lista'", 
        value="Este botão aparece abaixo de cada curso encontrado em uma busca. Clique nele para adicionar um curso à sua lista pessoal, que pode ser vista com `/meus_cursos`.", 
        inline=False
    )
    
    embed_ajuda.set_footer(text="Espero que ajude você a encontrar o curso perfeito!")
    
    await interaction.response.send_message(embed=embed_ajuda, ephemeral=True)


@bot.tree.command(name="meus_cursos", description="Mostra todos os cursos que você salvou.")
async def meus_cursos(interaction: discord.Interaction):
    user_id = interaction.user.id
    conexao = sqlite3.connect(DB_FILE)
    cursor = conexao.cursor()
    cursor.execute("SELECT course_title, course_url FROM inscricoes WHERE user_id = ?", (user_id,))
    cursos_do_usuario = cursor.fetchall()
    conexao.close()
    if not cursos_do_usuario:
        await interaction.response.send_message("Você ainda não salvou nenhum curso.", ephemeral=True)
        return
    embed = discord.Embed(title=f"📚 Meus Cursos Salvos", description=f"Sua lista de cursos, {interaction.user.mention}.", color=discord.Color.green())
    lista_formatada = ""
    for i, (titulo, url) in enumerate(cursos_do_usuario[:25], 1):
        titulo_curto = (titulo[:70] + '...') if len(titulo) > 70 else titulo
        lista_formatada += f"{i}. **[{titulo_curto}]({url})**\n"
    embed.add_field(name="Sua Lista:", value=lista_formatada, inline=False)
    await interaction.response.send_message(embed=embed, ephemeral=True)

# --- INICIA O BOT ---
if TOKEN == "": # Alterado para verificar se está vazio
    print("ERRO CRÍTICO: Por favor, configure seu token do Discord em uma variável de ambiente chamada DISCORD_TOKEN!")
else:
    bot.run(TOKEN)