"""BGE-M3 질문 임베딩과 읽기 전용 Qdrant 검색."""
from functools import lru_cache
import math
import os
from pathlib import Path
import httpx
from .scope import scope_exclusions, qdrant_scope_filter

class SearchError(RuntimeError):
    pass


def embedding_ready():
    return bool(os.getenv('EMBEDDING_URL')) or os.getenv('EMBEDDING_MODE') == 'local'

@lru_cache(maxsize=1)
def local_model():
    try:
        from FlagEmbedding import BGEM3FlagModel
    except ImportError:
        raise SearchError('로컬 BGE-M3 실행 패키지가 설치되지 않았습니다.') from None
    import torch
    torch.set_num_threads(4)
    model_path=os.getenv('BGE_MODEL_PATH', 'BAAI/bge-m3')
    if not Path(model_path).is_absolute() and model_path != 'BAAI/bge-m3':
        model_path=str(Path(__file__).resolve().parents[2] / model_path)
    return BGEM3FlagModel(model_path, use_fp16=False, devices=os.getenv('BGE_DEVICE','cpu'))


def embed(query):
    if os.getenv('EMBEDDING_URL'):
        headers = {}
        if os.getenv('EMBEDDING_API_KEY'):
            headers['Authorization'] = 'Bearer ' + os.environ['EMBEDDING_API_KEY']
        try:
            with httpx.Client(timeout=60) as client:
                r = client.post(os.environ['EMBEDDING_URL'], headers=headers,
                                json={'input': query, 'model': 'BAAI/bge-m3'})
                r.raise_for_status()
                data = r.json()
            vector = data['data'][0]['embedding']
            sparse = data.get('sparse')
        except (httpx.HTTPError, ValueError, KeyError, IndexError, TypeError):
            raise SearchError('질문 임베딩 API 응답을 확인해 주세요.') from None
    elif os.getenv('EMBEDDING_MODE') == 'local':
        try:
            data = local_model().encode([query], max_length=512, return_dense=True,
                                        return_sparse=True, return_colbert_vecs=False)
            vector = data['dense_vecs'][0].tolist()
            weights = data['lexical_weights'][0]
            sparse = {'indices': [int(k) for k in weights], 'values': [float(v) for v in weights.values()]}
        except SearchError:
            raise
        except Exception:
            raise SearchError('BGE-M3 모델 실행에 실패했습니다. 설치·모델 경로를 확인해 주세요.') from None
    else:
        raise SearchError('질문 임베딩 환경이 아직 없습니다. EMBEDDING_URL 또는 로컬 BGE-M3를 설정해 주세요.')
    if len(vector) != 1024 or any(not isinstance(v, (int,float)) or not math.isfinite(v) for v in vector):
        raise SearchError('BGE-M3 임베딩은 유한한 숫자 1024개여야 합니다.')
    return vector, sparse


def search(query, limit=8, department=None, admission_year=None):
    url = os.getenv('QDRANT_URL', '').rstrip('/')
    key = os.getenv('QDRANT_API_KEY')
    collection = os.getenv('QDRANT_COLLECTION')
    if not all((url, key, collection)):
        raise SearchError('Qdrant 주소·키·컬렉션을 설정해 주세요.')
    vector, sparse = embed(query)
    retrieval_limit=max(limit, 64) if department or admission_year else limit
    body = {'query': vector, 'using': 'bge_m3_dense', 'limit': retrieval_limit, 'with_payload': True}
    if sparse:
        body = {'prefetch': [{'query':vector, 'using':'bge_m3_dense', 'limit':max(24,retrieval_limit)},
                             {'query':sparse, 'using':'bge_m3_sparse', 'limit':max(24,retrieval_limit)}],
                'query':{'fusion':'rrf'}, 'limit':retrieval_limit, 'with_payload':True}
    scope_filter=qdrant_scope_filter(department, admission_year)
    if scope_filter:
        body['filter']=scope_filter
        for prefetch in body.get('prefetch',[]):
            prefetch['filter']=scope_filter
    try:
        with httpx.Client(timeout=30) as client:
            r = client.post(f'{url}/collections/{collection}/points/query', headers={'api-key':key}, json=body)
            r.raise_for_status()
            hits = r.json()['result']['points']
    except (httpx.HTTPError, ValueError, KeyError, TypeError):
        raise SearchError('Qdrant 검색에 실패했습니다. 서버 설정을 확인해 주세요.') from None
    keys = ('chunk_id','doc_id','title','source_url','source_type','section','text','applicability','dates',
            'course_rows','major_track','source_file','page','related_chunk_ids','quality_flags','metadata_review_required','table_structure')
    return [{**{k:h.get('payload',{}).get(k) for k in keys}, 'score':h.get('score')} for h in hits
            if h.get('payload',{}).get('text') and h.get('payload',{}).get('chunk_id')
            and not scope_exclusions(h.get('payload',{}), department, admission_year)][:limit]
