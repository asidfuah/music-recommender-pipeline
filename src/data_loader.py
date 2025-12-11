import os
import json
from typing import Dict, List, Any


def load_and_merge_playlists(playlists_dir: str, output_dir: str):
    """
    加载所有榜单 JSON 文件，支持子文件夹结构。

    参数:
        playlists_dir (str): 包含子文件夹的根目录路径（如 'netease_playlists'）
        output_dir (str): 输出中间文件的目录
    """
    all_songs: List[Dict[str, Any]] = []
    song_metadata: Dict[str, Dict[str, Any]] = {}

    # 确保输出目录存在
    os.makedirs(output_dir, exist_ok=True)

    # 遍历每个子文件夹（代表一个榜单）
    for folder_name in os.listdir(playlists_dir):
        folder_path = os.path.join(playlists_dir, folder_name)
        if not os.path.isdir(folder_path):
            continue  # 跳过非文件夹

        # 在子文件夹中查找 .json 文件
        json_file = None
        for file in os.listdir(folder_path):
            if file.endswith('.json'):
                json_file = os.path.join(folder_path, file)
                break

        if not json_file or not os.path.isfile(json_file):
            print(f"⚠️ 跳过文件夹 {folder_name}：未找到 .json 文件")
            continue

        print(f"正在加载榜单: {folder_name}")

        with open(json_file, 'r', encoding='utf-8') as f:
            try:
                data = json.load(f)
            except json.JSONDecodeError as e:
                print(f"⚠️ 跳过无效 JSON 文件 {json_file}: {e}")
                continue

        # 提取 playlist_info 和 songs
        playlist_info = data.get("playlist_info")
        if not playlist_info:
            print(f"⚠️ 文件 {json_file} 缺少 playlist_info，跳过")
            continue

        N = playlist_info.get("song_count")
        if not isinstance(N, int) or N <= 0:
            print(f"⚠️ 文件 {json_file} 的 song_count 无效: {N}，跳过")
            continue

        songs = data.get("songs", [])
        if not isinstance(songs, list):
            print(f"⚠️ 文件 {json_file} 的 songs 不是列表，跳过")
            continue

        # 处理每首歌
        for song in songs:
            if not isinstance(song, dict):
                continue
            song_id = str(song.get("id"))
            if not song_id:
                continue

            standardized_song = {
                "id": song_id,
                "name": song.get("name", ""),
                "artist": song.get("artist", ""),
                "type": song.get("type", ""),
                "duration": int(song.get("duration", 0)),
                "current_rank": int(song.get("current_rank", 0)),
                "last_rank": song.get("last_rank"),
                "stats": {
                    "comment_count": int(song.get("stats", {}).get("comment_count", 0))
                }
            }

            all_songs.append(standardized_song)

            # 构建元数据（后出现的会覆盖前面的）
            song_metadata[song_id] = {
                "N": N,
                "artist": standardized_song["artist"],
                "type": standardized_song["type"],
                "duration": standardized_song["duration"],
                "comment_count": standardized_song["stats"]["comment_count"],
                "current_rank": standardized_song["current_rank"],
                "last_rank": standardized_song["last_rank"]
            }

    # 保存结果
    all_songs_path = os.path.join(output_dir, "all_songs.json")
    with open(all_songs_path, 'w', encoding='utf-8') as f:
        json.dump(all_songs, f, ensure_ascii=False, indent=2)
    print(f"✅ 已保存 {len(all_songs)} 首歌曲到 {all_songs_path}")

    metadata_path = os.path.join(output_dir, "song_metadata.json")
    with open(metadata_path, 'w', encoding='utf-8') as f:
        json.dump(song_metadata, f, ensure_ascii=False, indent=2)
    print(f"✅ 已保存元数据（{len(song_metadata)} 首唯一歌曲）到 {metadata_path}")