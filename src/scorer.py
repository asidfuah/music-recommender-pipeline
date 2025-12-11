import json
import math
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity
from typing import Dict, List, Any, Union


def parse_last_rank(last_rank_val: Union[int, str]) -> Union[int, None]:
    """解析 last_rank 字段"""
    if isinstance(last_rank_val, int):
        return last_rank_val
    elif isinstance(last_rank_val, str) and "等于当前排名" in last_rank_val:
        return None
    else:
        return None


def compute_trend_score(current_rank: int, last_rank_raw: Union[int, str], N: int) -> float:
    """
    计算趋势得分（0~1）
    - 新歌（last_rank == 0）：上升空间大 → 高分
    - 上升快（last > current）：正向 delta → 高分
    - 下降或持平：0 分
    """
    last_rank = parse_last_rank(last_rank_raw)
    if last_rank is None:
        return 0.0

    if last_rank == 0:
        # 新上榜：假设上期排名为 N+1
        delta = (N + 1) - current_rank
        score = min(1.0, max(0.0, delta / N)) if N > 0 else 0.0
    else:
        delta = last_rank - current_rank
        if delta <= 0:
            score = 0.0
        else:
            max_possible_delta = N - 1  # 从最后一名到第一名
            score = min(1.0, delta / max_possible_delta) if max_possible_delta > 0 else 0.0
    return score


def compute_all_scores(
        user_profiles_file: str,
        song_metadata_file: str,
        all_songs_file: str,
        output_file: str,
        weights: Dict[str, float] = None
):
    """
    为每个用户-歌曲对计算推荐分数。

    Parameters:
        user_profiles_file: 用户画像文件
        song_metadata_file: 歌曲元数据（id → N, type, artist...）
        all_songs_file: 所有歌曲列表（用于补充 name 等字段，非必须但推荐）
        output_file: 输出原始打分文件
        weights: 各项权重，默认为 {"num": 1.0, "artist": 1.0, "type": 1.0, "trend": 0.8}
    """
    if weights is None:
        weights = {"num": 1.0, "artist": 1.0, "type": 1.0, "trend": 0.8}

    # 加载数据
    with open(user_profiles_file, 'r', encoding='utf-8') as f:
        user_profiles = json.load(f)

    with open(song_metadata_file, 'r', encoding='utf-8') as f:
        song_metadata = json.load(f)

    # 构建 id -> {name, artist} 映射（用于后续输出可读性）
    song_display = {}
    with open(all_songs_file, 'r', encoding='utf-8') as f:
        all_songs = json.load(f)
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
        num_vec = np.array(profile["num_vec"]).reshape(1, -1)  # shape: (1, 2)
        artist_set = set(profile["artists"])
        type_set = set(profile["types"])

        candidate_scores = []

        for song_id, meta in song_metadata.items():
            if song_id in liked_ids_set:
                continue  # 跳过已听

            # 1. 数值相似度
            song_vec = np.array([
                meta["duration"],
                math.log(1 + meta["comment_count"])
            ]).reshape(1, -1)
            num_sim = float(cosine_similarity(num_vec, song_vec)[0][0])

            # 2. 艺人匹配
            artist_sim = 1.0 if meta["artist"] in artist_set else 0.0

            # 3. 类型匹配
            type_sim = 1.0 if meta["type"] in type_set else 0.0

            # 4. 趋势得分
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

    # 保存结果
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(raw_scores, f, ensure_ascii=False, indent=2)

    print(f"✅ 已为 {len(raw_scores)} 个用户计算完所有候选歌曲得分，保存至 {output_file}")