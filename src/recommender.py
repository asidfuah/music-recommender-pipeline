# src/recommender.py
import json
import random
from typing import List, Dict, Any, Set, Union, Optional


def generate_recommendations(
        raw_scores_input: Union[str, Dict[str, List[Dict]]],
        users_input: Optional[Union[str, List[Dict]]] = None,
        all_songs_for_fallback: Optional[List[Dict]] = None,
        output_file: Optional[str] = None,
        top_k: int = 10,
        fallback_mode: str = "trending"
) -> List[Dict[str, Any]]:
    """
    生成推荐，支持冷启动 fallback。

    Parameters:
        raw_scores_input: 打分结果（文件路径 或 {user_id: [scores]} dict）
        users_input: （可选）用户列表，用于保持顺序和 liked_ids（文件或 list）
        all_songs_for_fallback: （可选）用于冷启动的完整歌曲池（当 raw_scores 为空时）
        output_file: （可选）输出 JSON 路径
        top_k: 推荐数量
        fallback_mode: "trending"（按 trend_score）或 "random"

    Returns:
        recommendations: [{user_id, recommendations: [...]}]
    """
    # 加载 raw_scores
    if isinstance(raw_scores_input, str):
        with open(raw_scores_input, 'r', encoding='utf-8') as f:
            raw_scores = json.load(f)
    else:
        raw_scores = raw_scores_input

    # 构建 user_liked_map 和 user_order
    user_liked_map: Dict[str, Set[str]] = {}
    user_order: List[str] = []

    if users_input is not None:
        if isinstance(users_input, str):
            with open(users_input, 'r', encoding='utf-8') as f:
                users_data = json.load(f)
            users_list = users_data.get("users", [])
        else:
            users_list = users_input

        for user in users_list:
            uid = user.get("user_id")
            if uid:
                user_order.append(uid)
                liked_ids = set(str(sid) for sid in user.get("liked_song_ids", []))
                user_liked_map[uid] = liked_ids
    else:
        # 若未提供 users_input，则按 raw_scores 的 key 顺序
        user_order = list(raw_scores.keys())

    # 获取候选歌曲池（用于 fallback）
    fallback_pool: List[Dict] = []
    if raw_scores:
        # 从任意用户的打分列表中提取（假设所有用户候选池相同）
        first_user_scores = next(iter(raw_scores.values()))
        fallback_pool = first_user_scores
    elif all_songs_for_fallback:
        # 如果 raw_scores 为空（如全新系统），用外部提供的歌曲池
        fallback_pool = all_songs_for_fallback
    else:
        fallback_pool = []

    # 对 fallback_pool 排序（仅使用 raw_scores 中已有的字段）
    if fallback_mode == "trending":
        # 使用 trend_score（来自 compute_all_scores）作为热度指标
        fallback_pool = sorted(
            fallback_pool,
            key=lambda x: x.get("trend_score", 0),
            reverse=True
        )
    elif fallback_mode == "random":
        fallback_pool = fallback_pool.copy()
        random.shuffle(fallback_pool)

    # 生成推荐
    recommendations: List[Dict[str, Any]] = []

    for user_id in user_order:
        liked_set = user_liked_map.get(user_id, set())

        if user_id in raw_scores and raw_scores[user_id]:
            # 正常推荐
            scores = raw_scores[user_id]
            sorted_songs = sorted(scores, key=lambda x: x["total_score"], reverse=True)
            top_songs = [s for s in sorted_songs if s["song_id"] not in liked_set][:top_k]
            rec_list = [
                {
                    "song_id": song["song_id"],
                    "name": song["name"],
                    "artist": song["artist"],
                    "recommend_score": song["total_score"]
                }
                for song in top_songs
            ]
        else:
            # 冷启动：从 fallback_pool 过滤已听后取 top_k
            filtered = [s for s in fallback_pool if s["song_id"] not in liked_set]
            selected = filtered[:top_k]
            rec_list = [
                {
                    "song_id": song["song_id"],
                    "name": song["name"],
                    "artist": song["artist"],
                    "recommend_score": -1.0  # 标记为 fallback
                }
                for song in selected
            ]

        recommendations.append({
            "user_id": user_id,
            "recommendations": rec_list
        })

    # 可选：保存到文件
    if output_file:
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(recommendations, f, ensure_ascii=False, indent=2)

    return recommendations