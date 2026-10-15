"""허깅페이스 Docker Space에 코드와 서버 환경 설정 배포."""
import argparse
import subprocess
from pathlib import Path
from dotenv import dotenv_values
from huggingface_hub import HfApi, CommitOperationAdd

ROOT = Path(__file__).resolve().parents[2]


def code_files():
    files = ['Dockerfile', '.dockerignore', 'backend/requirements.txt', 'backend/requirements-embedding.txt',
             'backend/scripts/build_course_index.py', 'backend/deploy/start.py']
    return files + [str(p.relative_to(ROOT)) for p in sorted((ROOT/'backend/app').glob('*.py'))]


def git_revision(files):
    """올리는 코드가 커밋된 상태인지 확인하고 브랜치·커밋을 돌려준다."""
    git = lambda *a: subprocess.run(['git', *a], cwd=ROOT, capture_output=True, text=True, check=True).stdout.strip()
    if git('status', '--porcelain', '--', *files):
        raise ValueError('커밋되지 않은 백엔드 변경이 있습니다. 커밋한 뒤 배포해 주세요.')
    return git('rev-parse', '--abbrev-ref', 'HEAD'), git('rev-parse', '--short', 'HEAD')


def deploy(repo_id, code_only=False):
    config = {**dotenv_values(ROOT / '.env'), **dotenv_values(ROOT / 'backend/.env')}
    token = config.get('HF_TOKEN')
    if not token:
        raise ValueError('.env에 Space 쓰기 권한이 있는 HF_TOKEN을 설정해 주세요.')
    api = HfApi(token=token)
    api.repo_info(repo_id, repo_type='space')
    files = code_files()
    if code_only:
        # 코드만 교체한다. Space의 Secrets·Variables는 건드리지 않는다.
        branch, commit = git_revision(files)
        if branch != 'main':
            print(f'주의: main이 아닌 {branch} 브랜치를 배포합니다.')
        message = f'코드 배포 ({branch} {commit})'
    else:
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
        message = '학사 문의 API 배포'
    ops = [CommitOperationAdd(path_in_repo=f, path_or_fileobj=str(ROOT/f)) for f in files]
    ops.append(CommitOperationAdd(path_in_repo='README.md', path_or_fileobj=str(ROOT/'backend/deploy/space.README.md')))
    api.create_commit(repo_id,repo_type='space',operations=ops,commit_message=message)
    print('Space 업로드 완료:',repo_id, f'({message})')


if __name__ == '__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('space',default='goblurry/academic-ai-agent',nargs='?')
    parser.add_argument('--code-only',action='store_true',help='Secrets·Variables는 그대로 두고 코드만 올립니다.')
    args=parser.parse_args()
    try:
        deploy(args.space, args.code_only)
    except ValueError as exc:
        raise SystemExit(f'배포 실패: {exc}')
    except Exception:
        raise SystemExit('배포 실패: HF_TOKEN 쓰기 권한, Space 주소 및 .env 설정을 확인해 주세요.')
