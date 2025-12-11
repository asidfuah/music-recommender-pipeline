# app.py
import streamlit as st
import json
import os

from src.scorer import compute_all_scores
from src.recommender import generate_recommendations
from src.user_profiler import build_user_profiles

# ----------------------------
# 配置路径
# ----------------------------
INPUT_DIR = "input"
OUTPUT_DIR = "output"
ALL_SONGS_PATH = os.path.join(OUTPUT_DIR, "all_songs.json")
METADATA_PATH = os.path.join(OUTPUT_DIR, "song_metadata.json")

os.makedirs(OUTPUT_DIR, exist_ok=True)

# ----------------------------
# 页面标题
# ----------------------------
st.set_page_config(page_title="🎵 Music Recommender", layout="wide")
st.title("🎵 Content-Based Music Recommendation System")

# ----------------------------
# 加载数据：metadata（用于计算） + all_songs（用于展示和搜索）
# ----------------------------
@st.cache_resource
def load_data_for_ui():
    # 检查文件是否存在
    if not os.path.exists(ALL_SONGS_PATH):
        st.error(f"❌ 找不到 {ALL_SONGS_PATH}，请先运行 `python run_pipeline.py`")
        st.stop()
    if not os.path.exists(METADATA_PATH):
        st.error(f"❌ 找不到 {METADATA_PATH}，请先运行 `python run_pipeline.py`")
        st.stop()

    # 加载 metadata（用于推荐计算）
    with open(METADATA_PATH, "r", encoding="utf-8") as f:
        song_meta = json.load(f)

    # 从 all_songs.json 构建 id -> (name, artist) 的映射
    with open(ALL_SONGS_PATH, "r", encoding="utf-8") as f:
        all_songs = json.load(f)

    id_to_info = {}
    for song in all_songs:
        sid = str(song.get("id"))
        if not sid:
            continue
        name = song.get("name", "").strip()
        artist = song.get("artist", "").strip()
        if name and sid not in id_to_info:
            id_to_info[sid] = {"name": name, "artist": artist}

    # 构建歌名索引（用于搜索）
    name_to_songs = {}
    for sid, info in id_to_info.items():
        key = info["name"].lower()
        if key not in name_to_songs:
            name_to_songs[key] = []
        name_to_songs[key].append({
            "id": sid,
            "name": info["name"],
            "artist": info["artist"]
        })

    return song_meta, id_to_info, name_to_songs

song_meta, id_to_info, name_to_songs = load_data_for_ui()

# ----------------------------
# 搜索函数
# ----------------------------
def search_songs(query: str):
    query = query.lower().strip()
    if not query:
        return []
    matches = []
    # 精确匹配
    if query in name_to_songs:
        matches.extend(name_to_songs[query])
    # 模糊匹配
    if not matches:
        for name_key, songs in name_to_songs.items():
            if query in name_key:
                matches.extend(songs)
    # 去重
    seen = set()
    unique = []
    for s in matches:
        if s["id"] not in seen:
            unique.append(s)
            seen.add(s["id"])
    return unique[:20]

# ----------------------------
# 用户输入
# ----------------------------
st.subheader("1. 输入你喜欢的歌曲名称（支持模糊搜索）")
user_query = st.text_input("例如: Sugar On My Tongue, 卡农, 亮剑", placeholder="输入歌曲名称...")

liked_song_ids = []
if user_query:
    results = search_songs(user_query)
    if results:
        st.write(f"🔍 找到 {len(results)} 首匹配歌曲：")
        for i, song in enumerate(results):
            checked = st.checkbox(
                f"{song['name']} — *{song['artist']}* (ID: {song['id']})",
                key=f"cb_{song['id']}_{i}"
            )
            if checked:
                liked_song_ids.append(song["id"])
    else:
        st.warning("未找到匹配的歌曲，请尝试其他关键词。")

top_k = st.slider("推荐数量", min_value=1, max_value=20, value=10)

# ----------------------------
# 生成推荐
# ----------------------------
if st.button("🎧 生成推荐"):
    if not liked_song_ids:
        st.warning("请至少选择一首喜欢的歌曲")
    else:
        # 构造临时用户
        mock_user = {"user_id": "web_user", "liked_song_ids": liked_song_ids}
        temp_users_path = os.path.join(INPUT_DIR, "temp_web_users.json")
        with open(temp_users_path, "w", encoding="utf-8") as f:
            json.dump([mock_user], f, ensure_ascii=False, indent=2)

        try:
            # 构造 minimal all_songs（仅包含用户喜欢的歌曲，用于构建画像）
            minimal_all_songs = []
            for sid in liked_song_ids:
                if sid in id_to_info:
                    info = id_to_info[sid]
                    # 从 song_meta 补充数值特征（如果存在）
                    meta = song_meta.get(sid, {})
                    minimal_all_songs.append({
                        "id": sid,
                        "name": info["name"],
                        "artist": info["artist"],
                        "type": meta.get("type", ""),
                        "duration": meta.get("duration", 0),
                        "stats": {
                            "comment_count": meta.get("comment_count", 0)  # ✅ 正确嵌套
                        },
                        # 其他字段可保留（如果 scorer 需要）
                        "current_rank": meta.get("current_rank", 0),
                        "last_rank": meta.get("last_rank", 0)
                    })

            user_profiles = build_user_profiles(temp_users_path, minimal_all_songs)
            raw_scores = compute_all_scores(user_profiles, song_meta)
            recommendations = generate_recommendations(raw_scores, top_k=top_k, fallback_mode="trending")

            # 显示结果（用 id_to_info 补全歌名和歌手）
            st.subheader("🎯 推荐结果")
            recs = recommendations[0]["recommendations"]
            if recs and recs[0].get("recommend_score", 0) == -1.0:
                st.info("⚠️ 冷启动模式：返回热门歌曲")

            for i, rec in enumerate(recs, 1):
                sid = rec["song_id"]
                display_name = rec.get("name") or id_to_info.get(sid, {}).get("name", sid)
                display_artist = rec.get("artist") or id_to_info.get(sid, {}).get("artist", "未知艺术家")
                score = rec.get("recommend_score")
                if score == -1.0:
                    score_str = "（热门推荐）"
                else:
                    score_str = f"（得分: {score:.3f}）"
                st.markdown(f"**{i}. {display_name}** — *{display_artist}* {score_str}")

        except Exception as e:
            st.error(f"❌ 出错了: {str(e)}")
        finally:
            if os.path.exists(temp_users_path):
                os.remove(temp_users_path)

# ----------------------------
# 统计信息
# ----------------------------
with st.expander("📊 歌曲库统计"):
    st.write(f"共收录 {len(id_to_info)} 首可搜索歌曲")
    st.write(f"推荐特征基于 {len(song_meta)} 首歌曲的元数据")