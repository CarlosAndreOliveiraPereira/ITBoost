# -*- coding: utf-8 -*-

import os

# --- CONFIGURAÇÕES GERAIS ---
TOKEN = os.getenv("TELEGRAM_TOKEN", "")
DB_FILE = "cursos_usuarios.db"

# --- LISTA DE SITES PARA BUSCA ---
# A estrutura agora é um dicionário com 'url', 'base', 'filter' e 'type' (free, paid, mixed)
SITES_DE_BUSCA = {
    "Udemy": {
        "url": "https://www.udemy.com/courses/search/?q={}&sort=relevance",
        "base": "https://www.udemy.com",
        "filter": "/course/",
        "type": "mixed" # Udemy tem cursos pagos e uma seção de cursos gratuitos
    },
    "Coursera": {
        "url": "https://www.coursera.org/search?query={}",
        "base": "https://www.coursera.org",
        "filter": "/learn/",
        "type": "mixed" # Coursera oferece cursos pagos, mas muitos com opção de auxílio financeiro ou gratuitos para ouvintes
    },
    "edX": {
        "url": "https://www.edx.org/search?q={}",
        "base": "https://www.edx.org",
        "filter": "/course/",
        "type": "mixed"
    },
    "Digital Innovation One": {
        "url": "https://www.dio.me/browse?search={}",
        "base": "https://www.dio.me",
        "filter": "/curso/",
        "type": "free"
    },
    "Fund. Bradesco Escola Virtual": {
        "url": "https://www.ev.org.br/catalogo-de-cursos?query={}",
        "base": "https://www.ev.org.br",
        "filter": "/curso/",
        "type": "free"
    },
    "Udacity": {
        "url": "https://www.udacity.com/courses/all?search={}",
        "base": "https://www.udacity.com",
        "filter": "/course/",
        "type": "mixed" # Famoso por Nanodegrees pagos, mas possui cursos gratuitos
    },
    "FutureLearn": {
        "url": "https://www.futurelearn.com/search?q={}",
        "base": "https://www.futurelearn.com",
        "filter": "/courses/",
        "type": "mixed"
    },
    "Alison": {
        "url": "https://alison.com/courses?query={}&category=it",
        "base": "https://alison.com",
        "filter": "/course/",
        "type": "free"
    },
    "Khan Academy": {
        "url": "https://www.khanacademy.org/search?page_search_query={}",
        "base": "https://www.khanacademy.org",
        "filter": "/x/", # Filtro mais genérico para os links da Khan Academy
        "type": "free"
    },
    "freeCodeCamp": {
        "url": "https://www.freecodecamp.org/news/search?query={}",
        "base": "https://www.freecodecamp.org/news",
        "filter": "/",
        "type": "free"
    },
    "Google Cursos": {
        "url": "https://skillshop.exceedlms.com/student/catalog/list?search={}",
        "base": "https://skillshop.exceedlms.com",
        "filter": "/student/path/",
        "type": "free"
    },
    "Alura": {
        "url": "https://www.alura.com.br/busca?query={}",
        "base": "https://www.alura.com.br",
        "filter": "/curso/",
        "type": "paid"
    },
    "DataCamp": {
        "url": "https://www.datacamp.com/search?q={}",
        "base": "https://www.datacamp.com",
        "filter": "/courses/",
        "type": "paid"
    },
    "Pluralsight": {
        "url": "https://www.pluralsight.com/search?q={}",
        "base": "https://www.pluralsight.com",
        "filter": "/courses/",
        "type": "paid"
    },
    "Class Central": {
        "url": "https://www.classcentral.com/search?q={}",
        "base": "https://www.classcentral.com",
        "filter": "/course/",
        "type": "mixed" # É um agregador, então inclui ambos
    },
}

SITES_PENTEST = {
    "HackerSec": {
        "url": "https://hackersec.com/cursos-gratuitos/",
        "base": "https://hackersec.com",
        "filter": "/curso/",
        "type": "free"
    },
    "Cybrary": {
        "url": "https://www.cybrary.it/catalog/all/", # Busca em todo o catálogo
        "base": "https://www.cybrary.it",
        "filter": "/course/",
        "type": "mixed" # Cybrary tem conteúdo gratuito e pago
    },
    "Hack The Box Academy": {
        "url": "https://academy.hackthebox.com/catalogue",
        "base": "https://academy.hackthebox.com",
        "filter": "/module/",
        "type": "mixed"
    },
}

# --- MAPEAMENTO DE CATEGORIAS PARA BUSCA ---
MAPA_CATEGORIAS = {
    "programacao": (["programação", "python", "javascript", "java", "desenvolvimento web"], "💻 Cursos de Programação"),
    "redes": (["redes de computadores", "ccna", "infraestrutura ti", "mikrotik"], "🌐 Cursos de Redes e Infraestrutura"),
    "cloud": (["aws", "azure", "google cloud", "cloud computing"], "☁️ Cursos de Cloud Computing"),
    "dados": (["sql", "banco de dados", "nosql", "mongodb", "postgresql"], "🗄️ Cursos de Banco de Dados"),
    "ciencia_dados": (["ciencia de dados", "machine learning", "inteligencia artificial", "deep learning"], "📊 Cursos de Ciência de Dados"),
    "devops": (["devops", "docker", "kubernetes", "ci/cd", "integração contínua"], "⚙️ Cursos de DevOps"),
    "seguranca": ([], "🛡️ Cursos de Segurança da Informação"), # Categoria especial tratada no handler
}