#!/bin/bash
# meedorri Portfolio Builder 시작 스크립트
# 사용법: ./start.sh

DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$DIR"

# 1. .env 파일에서 키 읽기 (있으면)
if [ -f "$DIR/.env" ]; then
  export $(grep -v '^#' "$DIR/.env" | xargs) 2>/dev/null
fi

# 2. API 키 확인 — 없으면 입력 받기
if [ -z "$ANTHROPIC_API_KEY" ]; then
  echo ""
  echo "Anthropic API 키가 필요합니다."
  echo "https://console.anthropic.com 에서 확인하세요."
  echo ""
  read -p "API 키를 입력하세요 (sk-ant-...): " KEY
  if [ -z "$KEY" ]; then
    echo "❌  키가 입력되지 않았습니다."; exit 1
  fi
  export ANTHROPIC_API_KEY="$KEY"
  # 다음번엔 묻지 않도록 .env 에 저장
  echo "ANTHROPIC_API_KEY=$KEY" > "$DIR/.env"
  echo "✅  .env 파일에 저장했습니다. 다음부터는 자동으로 불러옵니다."
fi

# 3. 기존 서버 종료
PID=$(lsof -ti:3301 2>/dev/null)
[ -n "$PID" ] && kill "$PID" 2>/dev/null && sleep 0.3

# 4. 서버 시작
python3 generate_server.py &
SERVER_PID=$!
sleep 0.8

# 5. 빌더 열기
open builder.html
echo "빌더가 열렸습니다. 종료하려면 Ctrl+C"

trap "kill $SERVER_PID 2>/dev/null; echo '서버 종료'" EXIT
wait $SERVER_PID
