# -*- coding: utf-8 -*-

import sqlite3
import logging
from typing import List, Tuple
from .config import DB_FILE

# Configuração do logger
logger = logging.getLogger(__name__)

def iniciar_banco_de_dados():
    """
    Cria as tabelas do banco de dados se elas não existirem.
    """
    try:
        with sqlite3.connect(DB_FILE) as conexao:
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
            logger.info("Banco de dados iniciado e tabela 'inscricoes' verificada.")
    except sqlite3.Error as e:
        logger.error(f"Erro ao iniciar o banco de dados: {e}")
        raise

def salvar_curso_usuario(user_id: int, course_title: str, course_url: str) -> bool:
    """
    Salva um curso na lista de um usuário. Retorna True se foi salvo com sucesso, False caso contrário.
    """
    try:
        with sqlite3.connect(DB_FILE) as conexao:
            cursor = conexao.cursor()
            cursor.execute(
                "INSERT INTO inscricoes (user_id, course_title, course_url) VALUES (?, ?, ?)",
                (user_id, course_title, course_url)
            )
            conexao.commit()
            logger.info(f"Curso '{course_title}' salvo para o usuário {user_id}.")
            return True
    except sqlite3.IntegrityError:
        logger.warning(f"Usuário {user_id} tentou salvar um curso duplicado: '{course_url}'.")
        return False  # Indica que o curso já existe
    except sqlite3.Error as e:
        logger.error(f"Erro de banco de dados ao salvar curso para o usuário {user_id}: {e}")
        return False

def obter_cursos_usuario(user_id: int) -> List[Tuple[str, str]]:
    """
    Obtém a lista de cursos salvos por um usuário.
    """
    try:
        with sqlite3.connect(DB_FILE) as conexao:
            cursor = conexao.cursor()
            cursor.execute("SELECT course_title, course_url FROM inscricoes WHERE user_id = ?", (user_id,))
            return cursor.fetchall()
    except sqlite3.Error as e:
        logger.error(f"Erro ao obter cursos do usuário {user_id} do banco de dados: {e}")
        return []