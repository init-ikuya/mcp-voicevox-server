#!/usr/bin/env python3
"""
MCP Server for VOICEVOX Text-to-Speech
"""

import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Optional

import httpx
from mcp.server.fastmcp import FastMCP

# Environment variables
VOICEVOX_URL = os.getenv("VOICEVOX_URL", "http://localhost:50021")
SPEAKER_ID = int(os.getenv("SPEAKER_ID", "8"))
AUTO_START_ENGINE = os.getenv("AUTO_START_ENGINE", "true").lower() == "true"

# Project directory (where docker-compose.yml is located)
PROJECT_DIR = Path(__file__).parent

# Initialize MCP server
mcp = FastMCP("voicevox")


def is_engine_running() -> bool:
    """Check if VOICEVOX Engine is running."""
    try:
        with httpx.Client(timeout=2.0) as client:
            response = client.get(f"{VOICEVOX_URL}/version")
            return response.status_code == 200
    except Exception:
        return False


def start_engine() -> bool:
    """Start VOICEVOX Engine using docker compose."""
    compose_file = PROJECT_DIR / "docker-compose.yml"
    if not compose_file.exists():
        print("docker-compose.yml not found, skipping auto-start", file=sys.stderr)
        return False

    try:
        subprocess.run(
            ["docker", "compose", "up", "-d"],
            cwd=PROJECT_DIR,
            check=True,
            capture_output=True,
        )
        return True
    except subprocess.CalledProcessError as e:
        print(f"Failed to start VOICEVOX Engine: {e}", file=sys.stderr)
        return False
    except FileNotFoundError:
        print("docker command not found", file=sys.stderr)
        return False


def ensure_engine_running() -> None:
    """Ensure VOICEVOX Engine is running, start if necessary."""
    if not AUTO_START_ENGINE:
        return

    if is_engine_running():
        return

    print("VOICEVOX Engine not running, starting...", file=sys.stderr)
    if start_engine():
        # Wait for engine to be ready
        for i in range(30):  # Wait up to 30 seconds
            time.sleep(1)
            if is_engine_running():
                print("VOICEVOX Engine started successfully", file=sys.stderr)
                return
        print("VOICEVOX Engine started but not responding yet", file=sys.stderr)


@mcp.tool()
async def list_speakers() -> str:
    """
    VOICEVOX Engineで利用可能なスピーカー（キャラクター）の一覧を取得します。

    Returns:
        スピーカー一覧の文字列
    """
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(f"{VOICEVOX_URL}/speakers")
            response.raise_for_status()
            speakers = response.json()

            lines: list[str] = []
            for speaker in speakers:
                name = speaker["name"]
                styles = speaker.get("styles", [])
                for style in styles:
                    style_name = style["name"]
                    style_id = style["id"]
                    lines.append(f"- {name}（{style_name}）: speaker_id={style_id}")

            return "利用可能なスピーカー一覧:\n" + "\n".join(lines)

    except httpx.ConnectError:
        return f"エラー: VOICEVOX Engine ({VOICEVOX_URL}) に接続できません。Dockerコンテナが起動しているか確認してください。"
    except httpx.HTTPStatusError as e:
        return f"エラー: VOICEVOX API エラー (status: {e.response.status_code})"
    except Exception as e:
        return f"エラー: {type(e).__name__}: {str(e)}"


@mcp.tool()
async def save_audio(
    text: str,
    output_path: str,
    speaker: Optional[int] = None,
    speed: Optional[float] = 1.0,
    pitch: Optional[float] = 0.0,
    intonation: Optional[float] = 1.0,
    volume: Optional[float] = 1.0,
) -> str:
    """
    テキストをVOICEVOXで音声合成し、WAVファイルとして保存します。

    Args:
        text: 読み上げるテキスト
        output_path: 保存先のファイルパス（.wav）
        speaker: スピーカーID（指定しない場合は環境変数SPEAKER_IDの値を使用。list_speakersで一覧を確認できます）
        speed: 話速 (0.5 〜 2.0, デフォルト: 1.0)
        pitch: 音高 (-0.15 〜 0.15, デフォルト: 0.0)
        intonation: 抑揚 (0.0 〜 2.0, デフォルト: 1.0)
        volume: 音量 (0.0 〜 2.0, デフォルト: 1.0)

    Returns:
        保存結果のメッセージ
    """
    speaker_id = speaker if speaker is not None else SPEAKER_ID
    if speed is None:
        speed = 1.0
    if pitch is None:
        pitch = 0.0
    if intonation is None:
        intonation = 1.0
    if volume is None:
        volume = 1.0

    # Validate parameter ranges
    if not 0.5 <= speed <= 2.0:
        return f"エラー: speedは0.5から2.0の範囲で指定してください (指定値: {speed})"
    if not -0.15 <= pitch <= 0.15:
        return f"エラー: pitchは-0.15から0.15の範囲で指定してください (指定値: {pitch})"
    if not 0.0 <= intonation <= 2.0:
        return f"エラー: intonationは0.0から2.0の範囲で指定してください (指定値: {intonation})"
    if not 0.0 <= volume <= 2.0:
        return f"エラー: volumeは0.0から2.0の範囲で指定してください (指定値: {volume})"

    # Ensure output path has .wav extension
    output_file = Path(output_path)
    if output_file.suffix.lower() != ".wav":
        output_file = output_file.with_suffix(".wav")

    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            # Step 1: Create audio query
            query_response = await client.post(
                f"{VOICEVOX_URL}/audio_query",
                params={"text": text, "speaker": speaker_id},
            )
            query_response.raise_for_status()
            audio_query = query_response.json()

            # Apply audio settings
            audio_query["speedScale"] = speed
            audio_query["pitchScale"] = pitch
            audio_query["intonationScale"] = intonation
            audio_query["volumeScale"] = volume

            # Step 2: Synthesize audio
            synthesis_response = await client.post(
                f"{VOICEVOX_URL}/synthesis",
                params={"speaker": speaker_id},
                json=audio_query,
            )
            synthesis_response.raise_for_status()
            audio_data = synthesis_response.content

            # Step 3: Save audio to file
            output_file.parent.mkdir(parents=True, exist_ok=True)
            output_file.write_bytes(audio_data)

            return f"音声ファイルを保存しました: {output_file}"

    except httpx.ConnectError:
        return f"エラー: VOICEVOX Engine ({VOICEVOX_URL}) に接続できません。Dockerコンテナが起動しているか確認してください。"
    except httpx.HTTPStatusError as e:
        return f"エラー: VOICEVOX API エラー (status: {e.response.status_code})"
    except PermissionError:
        return f"エラー: ファイルの書き込み権限がありません: {output_file}"
    except Exception as e:
        return f"エラー: {type(e).__name__}: {str(e)}"


@mcp.tool()
async def speak_text(
    text: str,
    speaker: Optional[int] = None,
    speed: Optional[float] = 1.0,
    pitch: Optional[float] = 0.0,
    intonation: Optional[float] = 1.0,
    volume: Optional[float] = 1.0,
) -> str:
    """
    テキストをVOICEVOXで音声合成し、スピーカーから再生します。

    Args:
        text: 読み上げるテキスト
        speaker: スピーカーID（指定しない場合は環境変数SPEAKER_IDの値を使用。list_speakersで一覧を確認できます）
        speed: 話速 (0.5 〜 2.0, デフォルト: 1.0)
        pitch: 音高 (-0.15 〜 0.15, デフォルト: 0.0)
        intonation: 抑揚 (0.0 〜 2.0, デフォルト: 1.0)
        volume: 音量 (0.0 〜 2.0, デフォルト: 1.0)

    Returns:
        再生結果のメッセージ
    """
    speaker_id = speaker if speaker is not None else SPEAKER_ID
    if speed is None:
        speed = 1.0
    if pitch is None:
        pitch = 0.0
    if intonation is None:
        intonation = 1.0
    if volume is None:
        volume = 1.0

    # Validate parameter ranges
    if not 0.5 <= speed <= 2.0:
        return f"エラー: speedは0.5から2.0の範囲で指定してください (指定値: {speed})"
    if not -0.15 <= pitch <= 0.15:
        return f"エラー: pitchは-0.15から0.15の範囲で指定してください (指定値: {pitch})"
    if not 0.0 <= intonation <= 2.0:
        return f"エラー: intonationは0.0から2.0の範囲で指定してください (指定値: {intonation})"
    if not 0.0 <= volume <= 2.0:
        return f"エラー: volumeは0.0から2.0の範囲で指定してください (指定値: {volume})"

    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            # Step 1: Create audio query
            query_response = await client.post(
                f"{VOICEVOX_URL}/audio_query",
                params={"text": text, "speaker": speaker_id},
            )
            query_response.raise_for_status()
            audio_query = query_response.json()

            # Apply audio settings
            audio_query["speedScale"] = speed
            audio_query["pitchScale"] = pitch
            audio_query["intonationScale"] = intonation
            audio_query["volumeScale"] = volume

            # Step 2: Synthesize audio
            synthesis_response = await client.post(
                f"{VOICEVOX_URL}/synthesis",
                params={"speaker": speaker_id},
                json=audio_query,
            )
            synthesis_response.raise_for_status()
            audio_data = synthesis_response.content

            # Step 3: Play audio using ffplay
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
                f.write(audio_data)
                temp_path = f.name

            try:
                subprocess.run(
                    ["ffplay", "-nodisp", "-autoexit", "-loglevel", "quiet", temp_path],
                    check=True,
                )
            finally:
                os.unlink(temp_path)

            return f"「{text[:20]}{'...' if len(text) > 20 else ''}」を再生しました"

    except httpx.ConnectError:
        return f"エラー: VOICEVOX Engine ({VOICEVOX_URL}) に接続できません。Dockerコンテナが起動しているか確認してください。"
    except httpx.HTTPStatusError as e:
        return f"エラー: VOICEVOX API エラー (status: {e.response.status_code})"
    except FileNotFoundError:
        return "エラー: ffplayが見つかりません。FFmpegをインストールしてください。"
    except subprocess.CalledProcessError as e:
        return f"エラー: 音声再生に失敗しました (code: {e.returncode})"
    except Exception as e:
        return f"エラー: {type(e).__name__}: {str(e)}"


if __name__ == "__main__":
    ensure_engine_running()
    mcp.run()
