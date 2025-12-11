# src/scorer.py
import json
import math
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity
from typing import Dict, List, Any, Union, Optional


def parse_last_rank(last_rank_val: Union[int, str]) -> Union[int, None]:
    if isinstance(last_rank_val, int):
        return last_rank_val
    elif isinstance(last_rank_val, str) and "等于当前排名" in last_rank_val:
        return None
    else:
        return None


def compute_trend_score(current_rank: int, last_rank_raw: Union[int, str], N: int) -> float:
    last_rank = parse_last_rank(last_rank_raw)
    if last_rank is None:
        return 0.0

    if last_rank == 0:
        delta = (N + 1) - current_rank
        score = min(1.0, max(0.0, delta / N)) if N > 0 else 0.0
    else:
        delta = last_rank - current_rank
        if delta <= 0:
            score = 0.0
        else:
            max_possible_delta = N - 1
            score = min(1.0, delta / max_possible_delta) if max_possible_delta > 0 else 0.0
    return score


def compute_all_scores(
        user_profiles_input: Union[str, Dict[str, Any]],
        song_metadata_input: Union[str, Dict[str, Any]],
        all_songs_input: Optional[Union[str, List[Dict]]] = None,
        output_file: Optional[str] = None,
        weights: Optional[Dict[str, float]] = None
) -> Dict[str, List[Dict]]:
    """
    为每个用户-歌曲对计算推荐分数。

    支持两种调用方式：
    - 文件模式：传入路径（用于 CLI）
    - 内存模式：传入 Python 对象（用于 Web UI）

    Parameters:
        user_profiles_input: 用户画像 dict 或 JSON 文件路径
        song_metadata_input: 歌曲元数据 dict 或 JSON 文件路径
        all_songs_input: （可选）用于补充 name/artist 的歌曲列表或路径
        output_file: （可选）保存原始打分结果的路径
        weights: 各项权重，默认 {"num": 1.0, "artist": 1.0, "type": 1.0, "trend": 0.8}

    Returns:
        raw_scores: {user_id: [候选歌曲打分列表]}
    """
    if weights is None:
        weights = {"num": 1.0, "artist": 1.0, "type": 1.0, "trend": 0.8}

    # 加载 user_profiles
    if isinstance(user_profiles_input, str):
        with open(user_profiles_input, 'r', encoding='utf-8') as f:
            user_profiles = json.load(f)
    else:
        user_profiles = user_profiles_input

    # 加载 song_metadata
    if isinstance(song_metadata_input, str):
        with open(song_metadata_input, 'r', encoding='utf-8') as f:
            song_metadata = json.load(f)
    else:
        song_metadata = song_metadata_input

    # 构建 song_display（用于可读性）
    song_display = {}
    if all_songs_input is not None:
        if isinstance(all_songs_input, str):
            with open(all_songs_input, 'r', encoding='utf-8') as f:
                all_songs = json.load(f)
        else:
            all_songs = all_songs_input

        for song in all_songs:
            sid = str(song["id"])
            if sid not in song_display:
                song_display[sid] = {
                    "name": song.get("name", ""),
                    "artist": song.get("artist", "")
                }

    raw_scores: Dict[str, List[Dict]] = {}

    for user_id, profile in user_profiles.items():
        liked_ids_set = set(str(sid) for sid in profile["liked_ids"])
        num_vec = np.array(profile["num_vec"]).reshape(1, -1)
        artist_set = set(profile["artists"])
        type_set = set(profile["types"])

        candidate_scores = []

        for song_id, meta in song_metadata.items():
            if song_id in liked_ids_set:
                continue

            # 数值相似度
            song_vec = np.array([
                meta["duration"],
                math.log(1 + meta["comment_count"])
            ]).reshape(1, -1)
            num_sim = float(cosine_similarity(num_vec, song_vec)[0][0])

            # 艺人 & 类型匹配
            artist_sim = 1.0 if meta["artist"] in artist_set else 0.0
            type_sim = 1.0 if meta["type"] in type_set else 0.0

            # 趋势得分
            trend_score = compute_trend_score(
                current_rank=meta["current_rank"],
                last_rank_raw=meta["last_rank"],
                N=meta["N"]
            )

            total_score = (
                    weights["num"] * num_sim +
                    weights["artist"] * artist_sim +
                    weights["type"] * type_sim +
                    weights["trend"] * trend_score
            )

            candidate_scores.append({
                "song_id": song_id,
                "name": song_display.get(song_id, {}).get("name", ""),
                "artist": song_display.get(song_id, {}).get("artist", ""),
                "num_sim": round(num_sim, 4),
                "artist_sim": artist_sim,
                "type_sim": type_sim,
                "trend_score": round(trend_score, 4),
                "total_score": round(total_score, 4)
            })

        raw_scores[user_id] = candidate_scores

    # 可选：保存到文件
    if output_file:
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(raw_scores, f, ensure_ascii=False, indent=2)

    return raw_scores