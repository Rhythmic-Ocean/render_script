import argparse
import osu
import sys
import os
import requests
import subprocess
from datetime import datetime
from load_env import ENV

ERROR_LOG = "render_errors.log"


def log_error(identifier, message):
    with open(ERROR_LOG, "a") as f:
        f.write(f"ID {identifier}: {message}\n")
    print(f"ERROR logged for {identifier}: {message}")


if os.name == "nt":
    DANSER_DIR = os.path.abspath("danser-win")
    DANSER_BIN = os.path.join(DANSER_DIR, "danser-cli.exe")
else:
    DANSER_DIR = os.path.abspath("danser_dir")
    DANSER_BIN = os.path.join(DANSER_DIR, "danser-cli")

# Ensure necessary directories exist
for folder in ["Songs", "Skins", "videos"]:
    os.makedirs(os.path.join(DANSER_DIR, folder), exist_ok=True)


def download_beatmap(beatmapset_id, songs_dir):
    url = f"https://api.nerinyan.moe/d/{beatmapset_id}"
    print(f"Downloading beatmapset {beatmapset_id} from {url}...")
    try:
        response = requests.get(url, stream=True, timeout=30)
        if response.status_code == 200:
            filename = f"{beatmapset_id}.osz"
            filepath = os.path.join(songs_dir, filename)
            with open(filepath, "wb") as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            print(f"Beatmapset {beatmapset_id} downloaded to {filepath}")
            return filepath
        else:
            return f"Failed to download beatmapset {beatmapset_id}: HTTP {response.status_code}"
    except Exception as e:
        return f"Exception during beatmap download: {str(e)}"


def render_score(client, score, beatmap_id, skin_name=None):
    try:
        if not score.replay:
            log_error(beatmap_id, f"Score {score.id} has no replay data available.")
            return

        print(f"Downloading replay for score {score.id}...")
        replay_data = client.get_replay_data_by_id_only(score.id, use_osrparse=False)
        replay_path = os.path.abspath(os.path.join("replays", f"replay_bm_{beatmap_id}_{score.id}.osr"))
        os.makedirs("replays", exist_ok=True)
        with open(replay_path, "wb") as f:
            f.write(replay_data)
        print(f"Replay saved to {replay_path}")

        beatmapset_id = (
            score.beatmapset.id
            if hasattr(score, "beatmapset") and score.beatmapset
            else None
        )
        if not beatmapset_id:
            beatmap_details = client.get_beatmap(beatmap_id)
            beatmapset_id = beatmap_details.beatmapset_id

        songs_dir = os.path.join(DANSER_DIR, "Songs")
        bm_error = download_beatmap(beatmapset_id, songs_dir)
        if isinstance(bm_error, str) and not bm_error.endswith(".osz"):
            log_error(beatmap_id, bm_error)
            return

        output_name = f"render_bm_{beatmap_id}_{score.id}"

        patch = '{"Recording": {"Encoder": "libx264", "FrameWidth": 2560, "Tune": "animation", "FrameHeight": 1440, "FPS": 60, "libx264": {"CRF": 20, "Preset": "slow"}, "aac": {"Bitrate": "192k"}}, "Playfield": {"Background": {"LoadStoryboards": false, "Dim": {"Normal": 1.0, "Breaks": 1.0}}}}'

        print(f"Running danser to record replay...")
        cmd = [
            DANSER_BIN,
            "-replay",
            replay_path,
            "-record",
            "-out",
            output_name,
            "-quickstart",
            "-noupdatecheck",
            "-sPatch",
            patch,
        ]

        if skin_name:
            cmd.extend(["-skin", skin_name])

        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            cwd=DANSER_DIR,
            bufsize=1,
            universal_newlines=True,
        )
        for line in process.stdout:
            print(f"[danser-score{score.id}] {line.strip()}")

        process.wait()
        if process.returncode == 0:
            video_path = os.path.join(DANSER_DIR, "videos", f"{output_name}.mp4")
            print(f"Rendering complete for score {score.id}! Video: {video_path}")
        else:
            log_error(
                beatmap_id, f"Danser failed with return code {process.returncode}"
            )

    except Exception as e:
        log_error(beatmap_id, f"Unexpected error during render: {str(e)}")


def process_score_id(client, score_id, skin_name=None):
    print(f"\n--- Processing Score ID {score_id} ---")
    try:
        score = client.get_score_by_id_only(score_id)
        if not score:
            log_error(score_id, "Score not found.")
            return

        beatmap_id = score.beatmap.id
        print(
            f"Score {score_id} found on beatmap {beatmap_id} ({score.beatmapset.title}) by {score.user.username}"
        )
        render_score(client, score, beatmap_id, skin_name)
    except Exception as e:
        log_error(score_id, f"Unexpected error processing score ID: {str(e)}")


def main():
    parser = argparse.ArgumentParser(description="Render osu! replays with danser")
    parser.add_argument("--skin", type=str, help="Skin name/file to use for rendering")
    parser.add_argument(
        "score_ids", type=int, nargs="+", help="Score IDs to render"
    )

    args = parser.parse_args()

    skin_name = args.skin
    score_ids = args.score_ids

    if skin_name:
        skin_path = os.path.join(DANSER_DIR, "Skins", skin_name)
        if not os.path.exists(skin_path):
            print(f"ERROR: Skin '{skin_name}' not found in {os.path.join(DANSER_DIR, 'Skins')}")
            sys.exit(1)

    client = osu.Client.from_credentials(
        ENV.OSU_CLIENT_ID, ENV.OSU_CLIENT_SECRET, ENV.REDIRECT_URL, osu.Scope.default()
    )
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(ERROR_LOG, "a") as f:
        f.write(f"\n--- New Render Session: {current_time} ---\n")

    for sid in score_ids:
        process_score_id(client, sid, skin_name)


if __name__ == "__main__":
    main()
