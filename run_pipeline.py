# run_pipeline.py
import os
from src.data_loader import load_and_merge_playlists
from src.user_profiler import build_user_profiles
from src.scorer import compute_all_scores
from src.recommender import generate_recommendations

if __name__ == "__main__":
    # 配置路径
    INPUT_DIR = "input"
    OUTPUT_DIR = "output"

    PLAYLISTS_DIR = os.path.join(INPUT_DIR, "netease_playlists")
    USERS_FILE = os.path.join(INPUT_DIR, "users.json")

    os.makedirs(OUTPUT_DIR, exist_ok=True)

    print("🔄 步骤 1/4: 加载并合并榜单数据...")
    load_and_merge_playlists(
        playlists_dir=PLAYLISTS_DIR,
        output_dir=OUTPUT_DIR
    )

    print("\n🔄 步骤 2/4: 构建用户画像...")
    build_user_profiles(
        USERS_FILE,  # ← users_input
        os.path.join(OUTPUT_DIR, "all_songs.json"),  # ← all_songs_input
        os.path.join(OUTPUT_DIR, "user_profiles.json")  # ← output_file
    )

    print("\n🔄 步骤 3/4: 计算歌曲推荐得分...")
    compute_all_scores(
        user_profiles_input=os.path.join(OUTPUT_DIR, "user_profiles.json"),   # ← 参数名已改
        song_metadata_input=os.path.join(OUTPUT_DIR, "song_metadata.json"),
        all_songs_input=os.path.join(OUTPUT_DIR, "all_songs.json"),
        output_file=os.path.join(OUTPUT_DIR, "raw_scores.json"),
        weights={
            "num": 1.0,
            "artist": 1.0,
            "type": 1.0,
            "trend": 0.8
        }
    )

    print("\n🔄 步骤 4/4: 生成最终推荐（含冷启动处理）...")
    generate_recommendations(
        raw_scores_input=os.path.join(OUTPUT_DIR, "raw_scores.json"),   # ← 参数名已改
        users_input=USERS_FILE,                                          # ← 支持路径
        output_file=os.path.join(OUTPUT_DIR, "recommendations.json"),
        top_k=10,
        fallback_mode="trending"
    )

    print("\n🎉 推荐系统运行完成！结果已保存至:")
    print(f"   → {os.path.join(OUTPUT_DIR, 'recommendations.json')}")