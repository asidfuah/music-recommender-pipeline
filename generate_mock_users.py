# generate_mock_users.py
import json
import random
import os
from typing import List, Set

# 动态导入 data_loader（避免循环依赖）
from src.data_loader import load_and_merge_playlists


def ensure_all_songs_exists(
        playlists_dir: str,
        output_dir: str,
        all_songs_file: str
):
    """确保 all_songs.json 存在，否则自动运行 data_loader"""
    if not os.path.exists(all_songs_file):
        print(f"⚠️ {all_songs_file} 不存在，正在从榜单生成...")
        os.makedirs(output_dir, exist_ok=True)
        load_and_merge_playlists(playlists_dir=playlists_dir, output_dir=output_dir)
    else:
        print(f"✅ 使用已有的 {all_songs_file}")


def generate_mock_users(
        playlists_dir: str,
        output_dir: str,
        users_output_file: str,
        num_users: int = 100,
        min_liked: int = 3,
        max_liked: int = 10,
        p_cold_start: float = 0.1,  # 冷启动概率（完全无喜欢歌曲）
        p_invalid_id: float = 0.05,  # 有效用户中，每首选无效ID的概率
        seed: int = 34
):
    """
    生成含冷启动和无效ID的模拟用户数据。

    Parameters:
        playlists_dir: 榜单目录（如 input/netease_playlists）
        output_dir: 输出目录（如 output/）
        users_output_file: 用户输出文件（如 input/users.json）
        num_users: 用户总数
        min_liked / max_liked: 正常用户喜欢歌曲数范围
        p_cold_start: 冷启动用户比例（liked_song_ids = []）
        p_invalid_id: 正常用户中，每首歌有 p_invalid_id 概率为无效ID
        seed: 随机种子
    """
    random.seed(seed)

    all_songs_file = os.path.join(output_dir, "all_songs.json")
    ensure_all_songs_exists(playlists_dir, output_dir, all_songs_file)

    # 加载所有有效 song_id
    with open(all_songs_file, 'r', encoding='utf-8') as f:
        all_songs = json.load(f)
    valid_song_ids: Set[str] = {str(song["id"]) for song in all_songs}
    print(f"✅ 有效歌曲池大小: {len(valid_song_ids)}")

    # 生成无效ID前缀（确保不会冲突）
    invalid_prefix = "invalid_"
    used_invalid = set()

    users = []
    num_cold = 0

    for i in range(1, num_users + 1):
        user_id = f"user_{i:03d}"

        # 决定是否为冷启动用户
        if random.random() < p_cold_start:
            liked_ids = []
            num_cold += 1
        else:
            # 正常用户：先选有效歌曲
            liked_count = random.randint(min_liked, max_liked)
            n_valid = min(liked_count, len(valid_song_ids))
            if n_valid == 0:
                liked_ids = []
            else:
                liked_ids = random.sample(list(valid_song_ids), n_valid)

            # 按概率替换部分为无效ID
            final_ids = []
            for sid in liked_ids:
                if random.random() < p_invalid_id:
                    # 生成唯一无效ID
                    while True:
                        fake_id = f"{invalid_prefix}{random.randint(1000000, 9999999)}"
                        if fake_id not in used_invalid:
                            used_invalid.add(fake_id)
                            final_ids.append(fake_id)
                            break
                else:
                    final_ids.append(sid)
            liked_ids = final_ids

        users.append({
            "user_id": user_id,
            "liked_song_ids": liked_ids
        })

    # 保存用户文件
    os.makedirs(os.path.dirname(users_output_file), exist_ok=True)
    with open(users_output_file, 'w', encoding='utf-8') as f:
        json.dump({"users": users}, f, ensure_ascii=False, indent=2)

    print(f"\n✅ 模拟用户生成完成!")
    print(f"   - 总用户数: {num_users}")
    print(f"   - 冷启动用户数 (liked_song_ids=[]): {num_cold}")
    print(f"   - 无效歌曲ID数量: {len(used_invalid)}")
    print(f"   - 输出文件: {users_output_file}")


if __name__ == "__main__":
    # ===== 配置区 =====
    PLAYLISTS_DIR = "input/netease_playlists"  # 你的榜单目录
    OUTPUT_DIR = "output"
    USERS_OUTPUT_FILE = "input/users.json"

    # 调整以下参数控制模拟行为
    NUM_USERS = 1000  # 总用户数
    MIN_LIKED = 3  # 正常用户最少喜欢数
    MAX_LIKED = 20 # 正常用户最多喜欢数
    P_COLD_START = 0.15  # 15% 冷启动用户（完全空）
    P_INVALID_ID = 0.1  # 正常用户中，10% 的歌是无效ID
    SEED = 34  # 随机种子
    # ==================

    generate_mock_users(
        playlists_dir=PLAYLISTS_DIR,
        output_dir=OUTPUT_DIR,
        users_output_file=USERS_OUTPUT_FILE,
        num_users=NUM_USERS,
        min_liked=MIN_LIKED,
        max_liked=MAX_LIKED,
        p_cold_start=P_COLD_START,
        p_invalid_id=P_INVALID_ID,
        seed=SEED
    )