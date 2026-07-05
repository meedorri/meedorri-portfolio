#!/usr/bin/env python3
"""
meedorri Generate Server — port 3301
claude CLI를 사용합니다. API 키 불필요.
"""

import os, json, re, glob, subprocess
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse

PORT   = 3301
FOLDER = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(FOLDER)  # 포트폴리오/ 의 상위 = git 저장소 루트
COPY_WIKI = os.path.join(REPO_ROOT, 'copy-wiki')  # 목소리 위키 (raw/wiki)
CLAUDE = os.path.expanduser('~/.local/bin/claude')  # claude CLI 경로
GIT    = '/usr/bin/git'

PROMPT_TEMPLATE = """{voice_rules}

## 실제 목소리 예시 (few-shot — 문체 패턴만 참고. 그대로 베끼거나 문장을 재사용하지 말 것)
{few_shot}

---

{image_refs}

위 사진들은 "미도리작업실(meedorri)" 브랜드의 "{folder_name}" 프로젝트입니다.
사진을 보고, 위 목소리 규칙과 예시의 문체 패턴을 참고해서 포트폴리오 상세 페이지용 콘텐츠를 아래 JSON 형식으로 작성해주세요.
다른 설명 없이 JSON만 반환하세요.

{{
  "title": "프로젝트 제목 (한국어 또는 브랜드명 그대로, 협업사명 포함 가능)",
  "category": "카테고리 (영어, 슬래시로 구분. 예: Product Design / Photography)",
  "year": "연도 4자리",
  "description": "프로젝트 설명 (한국어 2~3문장씩 두 단락. \\n\\n 으로 단락 구분)",
  "meta": [
    ["분류", "한국어"],
    ["연도", "YYYY"],
    ["역할", "미도리작업실이 맡은 역할 (한국어)"]
  ]
}}"""


def load_voice_context():
    """wiki/voice-rules.md 전체 + raw/voice-personal*.md few-shot 예시를 읽어온다."""
    rules_path = os.path.join(COPY_WIKI, 'wiki', 'voice-rules.md')
    rules = ''
    if os.path.exists(rules_path):
        with open(rules_path, encoding='utf-8') as f:
            rules = f.read().strip()

    examples = []
    for path in sorted(glob.glob(os.path.join(COPY_WIKI, 'raw', 'voice-personal*.md'))):
        with open(path, encoding='utf-8') as f:
            examples.append(f.read().strip())

    return rules, '\n\n'.join(examples)


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *_): pass

    def _cors(self):
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')

    def do_OPTIONS(self):
        self.send_response(200); self._cors(); self.end_headers()

    def do_POST(self):
        path = urlparse(self.path).path
        length = int(self.headers.get('Content-Length', 0))
        body = json.loads(self.rfile.read(length)) if length else {}

        if path == '/generate':
            try:
                result = generate(body)
                self.send_response(200)
                self.send_header('Content-Type', 'application/json'); self._cors(); self.end_headers()
                self.wfile.write(json.dumps(result, ensure_ascii=False).encode())
                print(f'  ✓ {body.get("folderName")} 생성 완료')
            except Exception as e:
                print(f'  ✗ 오류: {e}')
                self.send_response(500)
                self.send_header('Content-Type', 'application/json'); self._cors(); self.end_headers()
                self.wfile.write(json.dumps({'error': str(e)}, ensure_ascii=False).encode())
        elif path == '/publish':
            try:
                result = publish()
                self.send_response(200)
                self.send_header('Content-Type', 'application/json'); self._cors(); self.end_headers()
                self.wfile.write(json.dumps(result, ensure_ascii=False).encode())
                print(f'  ✓ 사이트에 반영 완료')
            except Exception as e:
                print(f'  ✗ publish 오류: {e}')
                self.send_response(500)
                self.send_header('Content-Type', 'application/json'); self._cors(); self.end_headers()
                self.wfile.write(json.dumps({'error': str(e)}, ensure_ascii=False).encode())
        else:
            self.send_response(404); self.end_headers()


def publish():
    subprocess.run([GIT, 'add', '-A'], cwd=REPO_ROOT, check=True, capture_output=True, text=True)

    status = subprocess.run(
        [GIT, 'status', '--porcelain'], cwd=REPO_ROOT, capture_output=True, text=True
    ).stdout

    if not status.strip():
        return {'pushed': False, 'message': '변경사항이 없습니다.'}

    commit = subprocess.run(
        [GIT, 'commit', '-m', 'Publish from builder'],
        cwd=REPO_ROOT, capture_output=True, text=True
    )
    if commit.returncode != 0:
        raise ValueError(commit.stderr.strip() or commit.stdout.strip() or 'git commit 실패')

    push = subprocess.run([GIT, 'push'], cwd=REPO_ROOT, capture_output=True, text=True)
    if push.returncode != 0:
        raise ValueError(push.stderr.strip() or 'git push 실패')

    return {'pushed': True}


def generate(data):
    folder_name = data.get('folderName', '')
    image_paths = data.get('images', [])[:4]

    # 절대 경로로 변환해서 @filepath 레퍼런스 구성
    refs = []
    for rel in image_paths:
        full = os.path.join(FOLDER, rel)
        if os.path.exists(full):
            refs.append(f'@{full}')

    if not refs:
        raise ValueError('사용 가능한 이미지가 없습니다.')

    voice_rules, few_shot = load_voice_context()

    prompt = PROMPT_TEMPLATE.format(
        voice_rules=voice_rules or '(voice-rules.md 없음)',
        few_shot=few_shot or '(few-shot 예시 없음)',
        image_refs='\n'.join(refs),
        folder_name=folder_name
    )

    result = subprocess.run(
        [CLAUDE, '-p', '--output-format', 'json'],
        input=prompt,
        capture_output=True, text=True, timeout=60
    )

    if result.returncode != 0:
        raise ValueError(result.stderr.strip() or 'claude CLI 오류')

    raw = json.loads(result.stdout).get('result', '')
    m   = re.search(r'\{[\s\S]*\}', raw)
    if not m:
        raise ValueError('응답에서 JSON을 파싱할 수 없습니다')
    return json.loads(m.group())


if __name__ == '__main__':
    if not os.path.exists(CLAUDE):
        print(f'❌  claude CLI를 찾을 수 없습니다: {CLAUDE}')
        raise SystemExit(1)
    print(f'✅  Generate 서버 실행 중 (port {PORT})')
    print(f'    claude: {CLAUDE}')
    print('    종료: Ctrl+C\n')
    HTTPServer(('localhost', PORT), Handler).serve_forever()
