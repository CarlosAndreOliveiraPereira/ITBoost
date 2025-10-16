# -*- coding: utf-8 -*-

import asyncio
import aiohttp
from bs4 import BeautifulSoup
import urllib.parse
import logging
from typing import List, Tuple, Literal

from .config import SITES_DE_BUSCA, SITES_PENTEST

# Configuração do logger
logger = logging.getLogger(__name__)

CourseType = Literal["free", "paid", "all"]

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

            title = a.get_text(strip=True) or (a.find('img') and a.find('img').get('alt', '').strip())

            if not title or len(title) < 5:
                title = link.split('/')[-1].split('?')[0].replace('-', ' ').replace('_', ' ').title()

            if title:
                cursos.append((title.strip(), link))

    return list(dict.fromkeys(cursos))

async def _scrape_site(session: aiohttp.ClientSession, url_template: str, base_url: str, filter_keyword: str) -> List[Tuple[str, str]]:
    """Coordena a busca e o parsing para um único site."""
    html = await _fetch_page(session, url_template)
    if html:
        return _parse_courses(html, base_url, filter_keyword)
    return []

async def pesquisar_cursos_online(termo: str, course_type: CourseType = "all") -> List[Tuple[str, str]]:
    """
    Pesquisa cursos em múltiplos sites de forma assíncrona, filtrando por tipo.
    """
    termo_formatado = urllib.parse.quote_plus(termo)

    sites_filtrados = {}
    if course_type == "all":
        sites_filtrados = SITES_DE_BUSCA
    else:
        sites_filtrados = {
            name: data for name, data in SITES_DE_BUSCA.items()
            if data['type'] == course_type or data['type'] == 'mixed'
        }

    async with aiohttp.ClientSession() as session:
        tasks = []
        for nome, data in sites_filtrados.items():
            url_de_busca = data['url'].format(termo_formatado)
            tasks.append(_scrape_site(session, url_de_busca, data['base'], data['filter']))
            logger.info(f"Iniciando busca por '{termo}' em {nome} (tipo: {course_type}).")

        resultados_por_site = await asyncio.gather(*tasks)

    todos_cursos = [curso for sublist in resultados_por_site for curso in sublist]
    logger.info(f"Busca por '{termo}' ({course_type}) concluída. Total de {len(todos_cursos)} resultados brutos.")
    return list(dict.fromkeys(todos_cursos))

async def pesquisar_cursos_pentest_especializados(course_type: CourseType = "all") -> List[Tuple[str, str]]:
    """
    Pesquisa cursos em sites de Pentest, filtrando por tipo.
    """
    sites_filtrados = {}
    if course_type == "all":
        sites_filtrados = SITES_PENTEST
    else:
        sites_filtrados = {
            name: data for name, data in SITES_PENTEST.items()
            if data['type'] == course_type or data['type'] == 'mixed'
        }

    async with aiohttp.ClientSession() as session:
        tasks = []
        for nome, data in sites_filtrados.items():
            # Alguns sites especializados não têm termo de busca, a URL é fixa
            url_de_busca = data['url'].format('')
            tasks.append(_scrape_site(session, url_de_busca, data['base'], data['filter']))
            logger.info(f"Iniciando busca em site especializado: {nome} (tipo: {course_type}).")

        resultados_por_site = await asyncio.gather(*tasks)

    todos_cursos = [curso for sublist in resultados_por_site for curso in sublist]
    logger.info(f"Busca em sites de Pentest ({course_type}) concluída. Total de {len(todos_cursos)} resultados brutos.")
    return list(dict.fromkeys(todos_cursos))