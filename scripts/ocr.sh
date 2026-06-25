#!/usr/bin/env bash
# ocr.sh — 用 macOS 自带 Vision.framework 做 OCR（本地、零上传、支持中文）
#
# 输入图片路径，输出识别到的文字（每行一条）。返回码 0=成功。
#
# 为什么用它：系统自带（macOS 12+），原生支持中英日韩，数据完全不出本机，
# 比 tesseract 中文准、比 5v 隐私好、比本地跑模型轻量。
#
# 实现：首次运行编译一个 Swift 小程序（缓存到 ~/.ai-daily/.bin/），之后直接复用。
#
# 用法:
#   ./ocr.sh <图片路径>
#
# 环境变量:
#   AI_DAILY_DIR  数据目录，默认 ~/.ai-daily（编译产物存这里的 .bin/）
set -euo pipefail

DATA_DIR="${AI_DAILY_DIR:-$HOME/.ai-daily}"
BIN_DIR="$DATA_DIR/.bin"
VISION_OCR="$BIN_DIR/vision_ocr"

IMG="${1:-}"
if [[ -z "$IMG" || ! -f "$IMG" ]]; then
  echo "用法: ocr.sh <图片路径>" >&2
  exit 2
fi

# --- 首次使用：编译 Swift OCR 程序（缓存复用） ---
if [[ ! -x "$VISION_OCR" ]]; then
  mkdir -p "$BIN_DIR"
  SRC="$BIN_DIR/vision_ocr.swift"
  cat > "$SRC" <<'SWIFT'
import Cocoa
import Vision
let args = CommandLine.arguments
guard args.count > 1 else { exit(1) }
let url = URL(fileURLWithPath: args[1])
guard let src = CGImageSourceCreateWithURL(url as CFURL, nil),
      let cg = CGImageSourceCreateImageAtIndex(src, 0, nil) else {
    fputs("无法加载图片\n", stderr); exit(1)
}
let req = VNRecognizeTextRequest()
req.recognitionLevel = .accurate
req.recognitionLanguages = ["zh-Hans","zh-Hant","en-US","ja-JP"]
let handler = VNImageRequestHandler(cgImage: cg)
try? handler.perform([req])
for obs in (req.results ?? []) {
    if let s = obs.topCandidates(1).first?.string, !s.isEmpty {
        print(s)
    }
}
SWIFT
  # 编译；失败则报错（缺 Xcode Command Line Tools 时会失败）
  if ! swiftc "$SRC" -o "$VISION_OCR" 2>/dev/null; then
    echo "ocr.sh: 编译 Vision OCR 失败。请装 Xcode Command Line Tools: xcode-select --install" >&2
    rm -f "$SRC" "$VISION_OCR"
    exit 3
  fi
fi

"$VISION_OCR" "$IMG"
