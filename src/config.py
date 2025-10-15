# -*- coding: utf-8 -*-

import os

# --- CONFIGURAÇÕES GERAIS ---
TOKEN = os.getenv("TELEGRAM_TOKEN", "")
DB_FILE = "cursos_usuarios.db"

# --- LISTA DE SITES PARA BUSCA ---
SITES_DE_BUSCA = {
    "Udemy (Grátis)": ("https://www.udemy.com/courses/search/?price=price-free&q={}&sort=relevance", "https://www.udemy.com", "/course/"),
    "Coursera": ("https://www.coursera.org/search?query={}", "https://www.coursera.org", "/learn/"),
    "edX": ("https://www.edx.org/search?q={}", "https://www.edx.org", "/course/"),
    "Digital Innovation One": ("https://www.dio.me/browse?search={}", "https://www.dio.me", "/curso/"),
    "Fund. Bradesco Escola Virtual": ("https://www.ev.org.br/catalogo-de-cursos?query={}", "https://www.ev.org.br", "/curso/"),
    "Udacity (Grátis)": ("https://www.udacity.com/courses/all?price=Free&search={}", "https://www.udacity.com", "/course/"),
    "FutureLearn": ("https://www.futurelearn.com/search?q={}", "https://www.futurelearn.com", "/courses/"),
    "Alison (TI)": ("https://alison.com/courses?query={}&category=it", "https://alison.com", "/course/"),
    # Adicionando novos sites focados em gratuidade e tecnologia
    "Khan Academy (Computação)": ("https://www.khanacademy.org/computing", "https://www.khanacademy.org", "/"),
    "freeCodeCamp": ("https://www.freecodecamp.org/news/search?query={}", "https://www.freecodecamp.org", "/"),
    "Google Cursos (Grátis)": ("https://skillshop.exceedlms.com/student/catalog/list?search={}&price=free", "https://skillshop.exceedlms.com", "/student/path/"),
}

SITES_PENTEST = {
    "HackerSec (Grátis)": ("https://hackersec.com/cursos-gratuitos/", "https://hackersec.com", "/curso/"),
    "Cybrary (Free Courses)": ("https://www.cybrary.it/catalog/free/", "https://www.cybrary.it", "/course/"),
    "Hack The Box Academy": ("https://academy.hackthebox.com/catalogue", "https://academy.hackthebox.com", "/"),
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