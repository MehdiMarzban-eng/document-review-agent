#!/bin/sh
set -eu
version='__VERSION__'
base="https://github.com/MehdiMarzban-eng/document-review-agent/releases/download/$version"
case "$(uname -s)" in
  Darwin)
    case "$(uname -m)" in arm64) platform=mac-arm64;; x86_64) platform=mac-x64;; *) echo 'Unsupported Mac processor'; exit 1;; esac
    data="$HOME/Library/Application Support/DocumentReviewLocal"
    ;;
  Linux)
    [ "$(uname -m)" = x86_64 ] || { echo 'This preview requires Linux x64.'; exit 1; }
    platform=linux-x64
    data="${XDG_DATA_HOME:-$HOME/.local/share}/document-review-local"
    ;;
  *) echo 'Unsupported operating system'; exit 1;;
esac
target="$data/app-$version"
app="$target/Document Review Local"
if [ ! -f "$app/installed.txt" ]; then
  mkdir -p "$target"
  archive="Document-Review-$platform.tar.gz"
  cd "$target"
  echo 'Downloading app dependencies...'
  curl --fail --location --proto '=https' --tlsv1.2 --output "$archive" "$base/$archive"
  curl --fail --location --proto '=https' --tlsv1.2 --output "$archive.sha256" "$base/$archive.sha256"
  if [ "$(uname -s)" = Darwin ]; then shasum -a 256 -c "$archive.sha256"; else sha256sum -c "$archive.sha256"; fi
  tar -xzf "$archive"
  touch "$app/installed.txt"
  rm -f "$archive" "$archive.sha256"
fi
cd "$app"
if [ "${DOCUMENT_REVIEW_DETACH:-0}" = 1 ]; then
  nohup ./python/bin/python3 -I ./launcher.py >/dev/null 2>&1 &
  exit 0
fi
exec ./python/bin/python3 -I ./launcher.py
