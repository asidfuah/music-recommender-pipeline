import json
import math
import numpy as np
from typing import Dict, List, Any, Set


def build_user_profiles(
        users_file: str,
        all_songs_file: str,
        output_file: str
):
    """
    构建用户画像。

    Parameters:
        users_file (str): 用户输入 JSON 文件路径
        all_songs_file (str): 所有歌曲数据文件路径
        output_file (str): 输出用户画像文件路径
    """
    # 1. 加载所有歌曲，建立 id -> song 映射
    with open(all_songs_file, 'r', encoding='utf-8') as f:
        all_songs = json.load(f)

    song_dict: Dict[str, Dict] = {}
    for song in all_songs:
        song_id = str(song["id"])
        # 如果重复，保留最后一个（与 data_loader 一致）
        song_dict[song_id] = song

    # 2. 加载用户数据
    with open(users_file, 'r', encoding='utf-8') as f:
        users_data = json.load(f)

    user_profiles: Dict[str, Dict] = {}

    for user in users_data.get("users", []):
        user_id = user.get("user_id")
        liked_ids_raw = user.get("liked_song_ids", [])

        if not user_id:
            print("⚠️ 跳过无 user_id 的用户记录")
            continue

        # 确保 liked_ids 是字符串列表
        liked_ids = [str(sid) for sid in liked_ids_raw]
        liked_songs = []

        for sid in liked_ids:
            if sid in song_dict:
                liked_songs.append(song_dict[sid])
            else:
                print(f"ℹ️ 用户 {user_id} 喜欢的歌曲 ID {sid} 不在歌曲池中，已忽略")

        if not liked_songs:
            print(f"⚠️ 用户 {user_id} 没有有效的喜欢歌曲，将生成空画像")
            user_profiles[user_id] = {
                "num_vec": [0.0, 0.0],
                "artists": [],
                "types": [],
                "liked_ids": []
            }
            continue

        # 计算数值特征
        durations = [s["duration"] for s in liked_songs]
        comments = [s["stats"]["comment_count"] for s in liked_songs]

        avg_duration = float(np.mean(durations))
        avg_comment_log = float(np.mean([math.log(1 + c) for c in comments]))

        # 提取文本偏好（去重）
        artists: List[str] = list(set(s["artist"] for s in liked_songs if s["artist"]))
        types: List[str] = list(set(s["type"] for s in liked_songs if s["type"]))

        user_profiles[user_id] = {
            "num_vec": [avg_duration, avg_comment_log],  # 存为 list 便于 JSON 序列化
            "artists": artists,
            "types": types,
            "liked_ids": liked_ids  # 保留原始顺序和全部 ID（含无效的）
        }

    # 3. 保存结果
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(user_profiles, f, ensure_ascii=False, indent=2)

    print(f"✅ 已为 {len(user_profiles)} 个用户生成画像，保存至 {output_file}")