#!/bin/bash
# meedorri Generate 서버 자동 시작 설치
# 한 번만 실행하면 맥 켤 때마다 서버가 자동으로 시작됩니다.

DIR="$(cd "$(dirname "$0")" && pwd)"
PLIST_ID="com.meedorri.builder"
PLIST_PATH="$HOME/Library/LaunchAgents/$PLIST_ID.plist"
PYTHON="$(which python3)"
SERVER="$DIR/generate_server.py"

echo "🔧 meedorri Generate 서버 설치 중..."

# 기존 설치 제거
launchctl unload "$PLIST_PATH" 2>/dev/null

# LaunchAgent plist 작성
cat > "$PLIST_PATH" << EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
  "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key>
  <string>$PLIST_ID</string>
  <key>ProgramArguments</key>
  <array>
    <string>$PYTHON</string>
    <string>$SERVER</string>
  </array>
  <key>RunAtLoad</key>
  <true/>
  <key>KeepAlive</key>
  <true/>
  <key>EnvironmentVariables</key>
  <dict>
    <key>PATH</key>
    <string>/Users/taei/.local/bin:/usr/local/bin:/usr/bin:/bin</string>
    <key>HOME</key>
    <string>$HOME</string>
  </dict>
  <key>StandardOutPath</key>
  <string>/tmp/meedorri-builder.log</string>
  <key>StandardErrorPath</key>
  <string>/tmp/meedorri-builder.log</string>
</dict>
</plist>
EOF

# 즉시 시작
launchctl load "$PLIST_PATH"
sleep 1

# 확인
if curl -s http://localhost:3301 >/dev/null 2>&1 || lsof -ti:3301 >/dev/null 2>&1; then
  echo "✅  설치 완료! 서버가 실행 중입니다."
  echo "    이제 builder.html을 열고 바로 Generate를 누르면 됩니다."
  echo "    맥을 재시작해도 자동으로 켜집니다."
else
  echo "⚠️  서버 시작을 확인하지 못했습니다. 로그를 확인하세요:"
  echo "    cat /tmp/meedorri-builder.log"
fi

echo ""
echo "제거하려면: launchctl unload $PLIST_PATH && rm $PLIST_PATH"
