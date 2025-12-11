# src/user_profiler.py
import json
import math
import numpy as np
from typing import Dict, List, Any, Union, Optional


def build_user_profiles(
        users_input: Union[str, List[Dict]],
        all_songs_input: Union[str, List[Dict]],
        output_file: Optional[str] = None
) -> Dict[str, Dict]:
    """
    构建用户画像。

    支持两种调用方式：
    - 文件模式：传入文件路径（用于 CLI）
    - 内存模式：传入 Python 对象（用于 Web UI）

    Parameters:
        users_input: 用户数据（JSON 文件路径 或 用户列表）
        all_songs_input: 歌曲数据（JSON 文件路径 或 歌曲列表）
        output_file: （可选）输出 JSON 路径，若为 None 则不保存

    Returns:
        user_profiles: {user_id: profile} 字典
    """
    # 1. 加载所有歌曲
    if isinstance(all_songs_input, str):
        with open(all_songs_input, 'r', encoding='utf-8') as f:
            all_songs = json.load(f)
    else:
        all_songs = all_songs_input

    song_dict: Dict[str, Dict] = {}
    for song in all_songs:
        song_id = str(song["id"])
        song_dict[song_id] = song

    # 2. 加载用户数据
    if isinstance(users_input, str):
        with open(users_input, 'r', encoding='utf-8') as f:
            users_data = json.load(f)

        # 兼容两种格式：
        if isinstance(users_data, list):
            users_list = users_data  # 直接是用户列表
        elif isinstance(users_data, dict):
            users_list = users_data.get("users", [])
        else:
            raise ValueError("users_input 必须是用户列表或包含 'users' 键的字典")
    else:
        users_list = users_input

    user_profiles: Dict[str, Dict] = {}

    for user in users_list:
        user_id = user.get("user_id")
        liked_ids_raw = user.get("liked_song_ids", [])

        if not user_id:
            continue  # 静默跳过（UI 不需要 print）

        liked_ids = [str(sid) for sid in liked_ids_raw]
        liked_songs = []

        for sid in liked_ids:
            if sid in song_dict:
                liked_songs.append(song_dict[sid])

        if not liked_songs:
            user_profiles[user_id] = {
                "num_vec": [0.0, 0.0],
                "artists": [],
                "types": [],
                "liked_ids": []
            }
            continue

        # 数值特征
        durations = [s["duration"] for s in liked_songs]
        comments = [s["stats"]["comment_count"] for s in liked_songs]

        avg_duration = float(np.mean(durations))
        avg_comment_log = float(np.mean([math.log(1 + c) for c in comments]))

        # 文本偏好（去重）
        artists = list(set(s["artist"] for s in liked_songs if s.get("artist")))
        types = list(set(s["type"] for s in liked_songs if s.get("type")))

        user_profiles[user_id] = {
            "num_vec": [avg_duration, avg_comment_log],
            "artists": artists,
            "types": types,
            "liked_ids": liked_ids
        }

    # 3. 可选：保存到文件
    if output_file:
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(user_profiles, f, ensure_ascii=False, indent=2)

    return user_profiles