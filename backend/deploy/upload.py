"""허깅페이스 Docker Space에 코드와 서버 환경 설정 배포."""
import argparse
from pathlib import Path
from dotenv import dotenv_values
from huggingface_hub import HfApi, CommitOperationAdd

ROOT = Path(__file__).resolve().parents[2]


def deploy(repo_id):
    config = {**dotenv_values(ROOT / '.env'), **dotenv_values(ROOT / 'backend/.env')}
    token = config.get('HF_TOKEN')
    if not token:
        raise ValueError('.env에 Space 쓰기 권한이 있는 HF_TOKEN을 설정해 주세요.')
    api = HfApi(token=token)
    api.repo_info(repo_id, repo_type='space')
    keys = ('DATABASE_URL', 'QDRANT_URL', 'QDRANT_API_KEY', 'QDRANT_COLLECTION', 'OPENAI_API_KEY',
            'DEMO_STUDENT_USERNAME', 'DEMO_STUDENT_PASSWORD', 'DEMO_STAFF_USERNAME', 'DEMO_STAFF_PASSWORD')
    for key in keys:
        if not config.get(key):
            raise ValueError(f'{key} 설정이 필요합니다.')
    # 공개 Variables에 연결 문자열이나 계정 비밀번호를 넣지 않는다.
    for key in keys:
        api.add_space_secret(repo_id, key=key, value=config[key])
    for key,value in {'OPENAI_MODEL':config.get('OPENAI_MODEL','gpt-4.1-mini'),
                      'CORS_ORIGINS':config.get('CORS_ORIGINS','http://localhost:5173,http://127.0.0.1:5173')}.items():
        api.add_space_variable(repo_id, key=key, value=value)
    files = ['Dockerfile', '.dockerignore', 'backend/requirements.txt', 'backend/requirements-embedding.txt',
             'backend/scripts/build_course_index.py', 'backend/deploy/start.py']
    files += [str(p.relative_to(ROOT)) for p in sorted((ROOT/'backend/app').glob('*.py'))]
    ops = [CommitOperationAdd(path_in_repo=f, path_or_fileobj=str(ROOT/f)) for f in files]
    ops.append(CommitOperationAdd(path_in_repo='README.md', path_or_fileobj=str(ROOT/'backend/deploy/space.README.md')))
    api.create_commit(repo_id,repo_type='space',operations=ops,commit_message='학사 문의 API 배포')
    print('Space 업로드 완료:',repo_id)


if __name__ == '__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('space',default='goblurry/academic-ai-agent',nargs='?')
    args=parser.parse_args()
    try:
        deploy(args.space)
    except Exception:
        raise SystemExit('배포 실패: HF_TOKEN 쓰기 권한, Space 주소 및 .env 설정을 확인해 주세요.')
