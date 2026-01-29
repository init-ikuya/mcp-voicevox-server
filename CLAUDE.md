# CLAUDE.md

このファイルは、Claude Code がこのリポジトリで作業する際のガイダンスを提供します。

## プロジェクト概要

VOICEVOX を使用してテキスト読み上げ・音声ファイル保存を行う MCP (Model Context Protocol) サーバーです。

## 技術スタック

- **言語**: Python 3.10+
- **パッケージマネージャー**: uv
- **MCP フレームワーク**: FastMCP
- **HTTP クライアント**: httpx
- **音声エンジン**: VOICEVOX Engine (Docker)
- **音声再生**: ffplay (FFmpeg)

## プロジェクト構造

```
mcp-voicevox-server/
├── server.py           # MCPサーバー本体
├── docker-compose.yml  # VOICEVOX Engine 用
├── pyproject.toml      # プロジェクト設定
├── uv.lock             # 依存関係ロックファイル
├── requirements.txt    # pip用依存関係
├── README.md           # ドキュメント
└── CLAUDE.md           # このファイル
```

## 開発コマンド

```bash
# 依存関係のインストール
uv sync

# サーバーの実行
uv run python server.py

# 依存関係の追加
uv add <package-name>
```

## VOICEVOX API フロー

1. `/audio_query` - テキストから音声クエリを生成
2. `/synthesis` - 音声クエリから WAV データを生成
3. `ffplay` - 生成された音声を再生

## 環境変数

| 変数名 | 説明 | デフォルト |
|--------|------|-----------|
| `VOICEVOX_URL` | VOICEVOX Engine の URL | `http://localhost:50021` |
| `SPEAKER_ID` | キャラクター ID | `8` (春日部つむぎ) |
| `AUTO_START_ENGINE` | 起動時に Docker を自動起動 | `true` |

## コーディング規約

- 型ヒントを使用する
- docstring は日本語で記述
- エラーハンドリングを適切に行う
- 非同期処理には `async/await` を使用
