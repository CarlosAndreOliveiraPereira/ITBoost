# -*- coding: utf-8 -*-

import asyncio
import aiohttp
from bs4 import BeautifulSoup
import urllib.parse
import logging
from typing import List, Tuple, Dict, Any

from .config import SITES_DE_BUSCA, SITES_PENTEST

# Configuração do logger
logger = logging.getLogger(__name__)

async def _fetch_page(session: aiohttp.ClientSession, url: str) -> str:
    """Função auxiliar para buscar o conteúdo de uma página de forma assíncrona."""
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
    try:
        async with session.get(url, headers=headers, timeout=15) as response:
            response.raise_for_status()
            return await response.text()
    except aiohttp.ClientError as e:
        logger.error(f"Erro de rede ao acessar {url}: {e}")
    except asyncio.TimeoutError:
        logger.warning(f"Timeout ao acessar {url}.")
    except Exception as e:
        logger.error(f"Erro desconhecido ao buscar {url}: {e}")
    return ""

def _parse_courses(html: str, base_url: str, filter_keyword: str) -> List[Tuple[str, str]]:
    """Função auxiliar para extrair cursos do HTML de uma página."""
    cursos = []
    soup = BeautifulSoup(html, "html.parser")
    for a in soup.find_all("a", href=True):
        href = a['href']
        if filter_keyword in href:
            link = href if href.startswith("http") else urllib.parse.urljoin(base_url, href)

            # Tenta extrair o título de várias formas
            title = a.get_text(strip=True)
            if not title:
                img = a.find('img')
                if img and img.get('alt'):
                    title = img['alt'].strip()

            # Se ainda não houver título, cria um a partir do link
            if not title or len(title) < 5:
                title = link.split('/')[-1].split('?')[0].replace('-', ' ').replace('_', ' ').title()

            if title:
                cursos.append((title, link))

    return list(dict.fromkeys(cursos)) # Remove duplicatas mantendo a ordem

async def _scrape_site(session: aiohttp.ClientSession, url: str, base_url: str, filter_keyword: str) -> List[Tuple[str, str]]:
    """Coordena a busca e o parsing para um único site."""
    html = await _fetch_page(session, url)
    if html:
        return _parse_courses(html, base_url, filter_keyword)
    return []

async def pesquisar_cursos_online(termo: str) -> List[Tuple[str, str]]:
    """
    Pesquisa cursos em múltiplos sites de forma assíncrona.
    """
    termo_formatado = urllib.parse.quote_plus(termo)
    async with aiohttp.ClientSession() as session:
        tasks = []
        for nome, (url_template, base, filtro) in SITES_DE_BUSCA.items():
            url_de_busca = url_template.format(termo_formatado)
            tasks.append(_scrape_site(session, url_de_busca, base, filtro))
            logger.info(f"Iniciando busca por '{termo}' em {nome}.")

        resultados_por_site = await asyncio.gather(*tasks)

    todos_cursos = [curso for sublist in resultados_por_site for curso in sublist]
    logger.info(f"Busca por '{termo}' concluída. Total de {len(todos_cursos)} resultados brutos encontrados.")
    return list(dict.fromkeys(todos_cursos))

async def pesquisar_cursos_pentest_especializados() -> List[Tuple[str, str]]:
    """
    Pesquisa cursos em sites especializados em Pentest de forma assíncrona.
    """
    async with aiohttp.ClientSession() as session:
        tasks = []
        for nome, (url_fixa, base, filtro) in SITES_PENTEST.items():
            tasks.append(_scrape_site(session, url_fixa, base, filtro))
            logger.info(f"Iniciando busca em site especializado: {nome}.")

        resultados_por_site = await asyncio.gather(*tasks)

    todos_cursos = [curso for sublist in resultados_por_site for curso in sublist]
    logger.info(f"Busca em sites de Pentest concluída. Total de {len(todos_cursos)} resultados brutos.")
    return list(dict.fromkeys(todos_cursos))