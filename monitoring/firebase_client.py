"""
Cliente Firebase Admin SDK.

Inicializa o app Firebase a partir das credenciais configuradas em .env:
  FIREBASE_CREDENTIALS_PATH  – caminho para o JSON da service account
  FIREBASE_PROJECT_ID        – ID do projeto Firebase (opcional se estiver no JSON)
"""

import os
import logging

logger = logging.getLogger(__name__)

_db = None  # instância lazy do Firestore client


def _init_firebase():
    """Inicializa o Firebase Admin SDK (idempotente)."""
    import firebase_admin
    from firebase_admin import credentials, firestore

    if firebase_admin._DEFAULT_APP_NAME in firebase_admin._apps:
        return firestore.client()

    creds_path = os.getenv("FIREBASE_CREDENTIALS_PATH", "")
    project_id = os.getenv("FIREBASE_PROJECT_ID", "")

    if not creds_path or not os.path.isfile(creds_path):
        raise FileNotFoundError(
            f"Credenciais Firebase não encontradas. "
            f"Defina FIREBASE_CREDENTIALS_PATH no .env apontando para o JSON da service account. "
            f"Valor atual: '{creds_path}'"
        )

    cred = credentials.Certificate(creds_path)
    kwargs = {}
    if project_id:
        kwargs["project"] = project_id

    firebase_admin.initialize_app(cred, kwargs)
    logger.info("Firebase Admin SDK inicializado com sucesso.")
    return firestore.client()


def get_db():
    """Retorna o cliente Firestore, inicializando se necessário."""
    global _db
    if _db is None:
        _db = _init_firebase()
    return _db


def save_document(collection: str, data: dict, doc_id: str = None) -> str:
    """
    Salva um documento no Firestore.

    Args:
        collection: caminho da coleção (ex: 'monitoring/flask_api/system_metrics')
        data: dicionário com os dados
        doc_id: ID do documento (auto-gerado se None)

    Returns:
        ID do documento criado
    """
    from firebase_admin import firestore as fs

    db = get_db()
    col_ref = db.collection(collection)

    # Adiciona server timestamp automaticamente
    data["_saved_at"] = fs.SERVER_TIMESTAMP

    if doc_id:
        col_ref.document(doc_id).set(data)
        return doc_id
    else:
        _, doc_ref = col_ref.add(data)
        return doc_ref.id


def set_document(collection: str, doc_id: str, data: dict, merge: bool = True) -> None:
    """
    Cria ou atualiza um documento com ID fixo no Firestore.

    Args:
        collection: caminho da coleção
        doc_id: ID do documento
        data: dicionário com os dados
        merge: se True, mescla com dados existentes (padrão)
    """
    from firebase_admin import firestore as fs

    db = get_db()
    data["_updated_at"] = fs.SERVER_TIMESTAMP
    db.collection(collection).document(doc_id).set(data, merge=merge)
