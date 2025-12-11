import json
import random
from typing import List, Dict, Any, Set


def generate_recommendations(
        raw_scores_file: str,
        users_file: str,
        output_file: str,
        top_k: int = 10,
        fallback_mode: str = "trending"  # "trending" 或 "random"
):
    """
    生成推荐，支持冷启动 fallback。

    Parameters:
        raw_scores_file: 原始打分文件
        users_file: 用户输入文件（用于顺序和 liked_ids）
        output_file: 输出文件
        top_k: 推荐数量
        fallback_mode: 冷启动策略 ("trending" / "random")
    """
    with open(raw_scores_file, 'r', encoding='utf-8') as f:
        raw_scores = json.load(f)

    # 加载用户 liked_ids（用于冷启动时过滤已听）
    user_liked_map: Dict[str, Set[str]] = {}
    try:
        with open(users_file, 'r', encoding='utf-8') as f:
            users_data = json.load(f)
        for user in users_data.get("users", []):
            uid = user.get("user_id")
            if uid:
                user_liked_map[uid] = set(str(sid) for sid in user.get("liked_song_ids", []))
    except Exception as e:
        print(f"⚠️ 无法加载 liked_ids 用于冷启动过滤: {e}")

    # 获取所有候选歌曲（来自 raw_scores 的任意用户，因所有用户共享同一候选池）
    all_candidate_songs = []
    if raw_scores:
        first_user = next(iter(raw_scores.values()))
        all_candidate_songs = first_user  # 每个用户都有完整候选列表
    else:
        print("❌ raw_scores 为空，无法生成 fallback 推荐")
        all_candidate_songs = []

    # 构建全局 fallback 候选池（按策略排序）
    if fallback_mode == "trending":
        # 按 trend_score + comment_count 综合排序
        fallback_pool = sorted(
            all_candidate_songs,
            key=lambda x: (
                    x.get("trend_score", 0) * 0.7 +
                    (x.get("comment_count", 0) > 0) * 0.3  # 或直接用 log(comment)
            ),
            reverse=True
        )
    elif fallback_mode == "random":
        fallback_pool = all_candidate_songs.copy()
        random.shuffle(fallback_pool)
    else:
        fallback_pool = all_candidate_songs  # 默认按原序

    # 获取用户顺序
    user_order = []
    try:
        with open(users_file, 'r', encoding='utf-8') as f:
            users_data = json.load(f)
        user_order = [user["user_id"] for user in users_data.get("users", [])]
    except:
        user_order = list(raw_scores.keys())

    recommendations: List[Dict[str, Any]] = []

    for user_id in user_order:
        liked_set = user_liked_map.get(user_id, set())

        if user_id in raw_scores and len(raw_scores[user_id]) > 0:
            # 正常用户：已有打分
            scores = raw_scores[user_id]
            sorted_songs = sorted(scores, key=lambda x: x["total_score"], reverse=True)
            top_songs = sorted_songs[:top_k]
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
            # 冷启动用户：使用 fallback
            filtered_fallback = [
                song for song in fallback_pool
                if song["song_id"] not in liked_set
            ]
            selected = filtered_fallback[:top_k]
            rec_list = [
                {
                    "song_id": song["song_id"],
                    "name": song["name"],
                    "artist": song["artist"],
                    "recommend_score": -1.0  # 标记为 fallback
                }
                for song in selected
            ]
            if not rec_list:
                print(f"ℹ️ 冷启动用户 {user_id} 无可用 fallback 歌曲")

        recommendations.append({
            "user_id": user_id,
            "recommendations": rec_list
        })

    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(recommendations, f, ensure_ascii=False, indent=2)

    print(f"✅ 已生成 Top-{top_k} 推荐（冷启动策略: {fallback_mode}），保存至 {output_file}")