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

    # 确保输出目录存在
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    print("🔄 步骤 1/4: 加载并合并榜单数据...")
    load_and_merge_playlists(
        playlists_dir=PLAYLISTS_DIR,
        output_dir=OUTPUT_DIR
    )

    print("\n🔄 步骤 2/4: 构建用户画像...")
    build_user_profiles(
        users_file=USERS_FILE,
        all_songs_file=os.path.join(OUTPUT_DIR, "all_songs.json"),
        output_file=os.path.join(OUTPUT_DIR, "user_profiles.json")
    )

    print("\n🔄 步骤 3/4: 计算歌曲推荐得分...")
    compute_all_scores(
        user_profiles_file=os.path.join(OUTPUT_DIR, "user_profiles.json"),
        song_metadata_file=os.path.join(OUTPUT_DIR, "song_metadata.json"),
        all_songs_file=os.path.join(OUTPUT_DIR, "all_songs.json"),
        output_file=os.path.join(OUTPUT_DIR, "raw_scores.json"),
        weights={
            "num": 1.0,  # 数值相似度权重
            "artist": 1.0,  # 艺人匹配权重
            "type": 1.0,  # 类型匹配权重
            "trend": 0.8  # 趋势得分权重
        }
    )

    print("\n🔄 步骤 4/4: 生成最终推荐（含冷启动处理）...")
    generate_recommendations(
        raw_scores_file=os.path.join(OUTPUT_DIR, "raw_scores.json"),
        users_file=USERS_FILE,
        output_file=os.path.join(OUTPUT_DIR, "recommendations.json"),
        top_k=10,
        fallback_mode="trending"  # 冷启动策略：trending 或 random
    )

    print("\n🎉 推荐系统运行完成！结果已保存至:")
    print(f"   → {os.path.join(OUTPUT_DIR, 'recommendations.json')}")