# mcp-voicevox-server-python

Claude Code の返答を **VOICEVOX** で読み上げるための MCP (Model Context Protocol) サーバーです。
日本語の自然な合成音声により、開発中のフィードバックを耳で受け取ることが可能になります。

---

## 🚀 概要

このプロジェクトは、Claude Code からの指示を受け取り、Docker 上で動作する VOICEVOX Engine を介して音声を生成、ローカルの `ffplay` で再生します。

### システム構成
- **Client**: Claude Code
- **MCP Server**: Python (FastMCP)
- **Engine**: VOICEVOX Engine (Docker)
- **Player**: ffplay (FFmpeg)

---

## 🛠 前提条件

- **Python**: 3.10 以上
- **uv**: パッケージマネージャー（推奨）
- **Docker**: VOICEVOX Engine の実行に必要
- **FFmpeg**: 音声再生用の `ffplay` コマンドを使用
  - macOS: `brew install ffmpeg`
  - Windows: `choco install ffmpeg` / `scoop install ffmpeg`
  - Linux: `sudo apt install ffmpeg`

---

## 📦 セットアップ

### 1. 依存関係のインストール

#### uv を使用する場合（推奨）
```bash
uv sync
```

#### pip を使用する場合
```bash
pip install -r requirements.txt
```

---

## ⚙️ Claude Code 設定

`~/.claude.json` に以下の設定を追加します。

### uv を使用する場合（推奨）
```json
{
  "mcpServers": {
    "voicevox": {
      "command": "uv",
      "args": ["run", "--directory", "/path/to/mcp-voicevox-server", "python", "server.py"],
      "env": {
        "VOICEVOX_URL": "http://localhost:50021",
        "SPEAKER_ID": "3"
      }
    }
  }
}
```

### python を直接使用する場合
```json
{
  "mcpServers": {
    "voicevox": {
      "command": "python3",
      "args": ["/path/to/mcp-voicevox-server/server.py"],
      "env": {
        "VOICEVOX_URL": "http://localhost:50021",
        "SPEAKER_ID": "3"
      }
    }
  }
}
```

### 環境変数
| 変数名 | 説明 | デフォルト |
|--------|------|-----------|
| `VOICEVOX_URL` | Engine のアドレス | `http://localhost:50021` |
| `SPEAKER_ID` | キャラクターID | `3` |
| `AUTO_START_ENGINE` | 自動的にDockerを起動するか | `true` |

### キャラクター一覧（一部）
| ID | キャラクター |
|----|-------------|
| 2  | 四国めたん |
| 3  | ずんだもん |
| 8  | 春日部つむぎ |

---

## 🐳 VOICEVOX Engine の自動起動

MCP サーバー起動時に VOICEVOX Engine が動作していない場合、自動的に Docker で起動します。

### 仕組み
1. サーバー起動時に `VOICEVOX_URL` への接続をチェック
2. 接続できない場合、`docker compose up -d` を実行
3. Engine が起動するまで最大30秒待機

### 手動で起動する場合

自動起動を無効にしたい場合は、環境変数を設定してください：

```json
{
  "env": {
    "AUTO_START_ENGINE": "false"
  }
}
```

手動で Docker を起動する場合：

```bash
# docker compose を使用
docker compose up -d

# または直接実行
docker run --rm -d -p 50021:50021 voicevox/voicevox_engine:cpu-ubuntu20.04-latest
```

---

## 🛠 提供されるツール

### `speak_text`

テキストを VOICEVOX で音声合成し、スピーカーから再生します。

**引数:**
- `text` (string, 必須): 読み上げるテキスト
- `speed` (number, optional): 話速 (0.5 〜 2.0, デフォルト: 1.0)
- `pitch` (number, optional): 音高 (-0.15 〜 0.15, デフォルト: 0.0)
- `intonation` (number, optional): 抑揚 (0.0 〜 2.0, デフォルト: 1.0)
- `volume` (number, optional): 音量 (0.0 〜 2.0, デフォルト: 1.0)

**戻り値:**
- 再生完了メッセージまたはエラーメッセージ

### `save_audio`

テキストを VOICEVOX で音声合成し、WAV ファイルとして保存します。

**引数:**
- `text` (string, 必須): 読み上げるテキスト
- `output_path` (string, 必須): 保存先のファイルパス（.wav）
- `speed` (number, optional): 話速 (0.5 〜 2.0, デフォルト: 1.0)
- `pitch` (number, optional): 音高 (-0.15 〜 0.15, デフォルト: 0.0)
- `intonation` (number, optional): 抑揚 (0.0 〜 2.0, デフォルト: 1.0)
- `volume` (number, optional): 音量 (0.0 〜 2.0, デフォルト: 1.0)

**戻り値:**
- 保存完了メッセージまたはエラーメッセージ

---

## 💡 使い方

Claude Code 上で直接指示してください。

```
「今のコード変更の概要を speak_text で教えて」
「テストが通ったら『お疲れ様なのだ』と喋って」
```

### 自動化のヒント

`.claude/settings.json` や `CLAUDE.md` に以下のようなシステムプロンプトを追加すると便利です：

> 各回答の最後には必ず speak_text ツールを使用して、回答の重要なポイントを1文で読み上げてください。

---

## 📝 ライセンス

MIT
