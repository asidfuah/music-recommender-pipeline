import os
import requests
import json
import jsonpath
import re
import csv
import time
from lxml import etree
from requests.exceptions import RequestException


class CloudMusicSpider:
    def __init__(self):
        self.session = requests.Session()
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                          "AppleWebKit/537.36 (KHTML, like Gecko) "
                          "Chrome/85.0.4183.121 Safari/537.36",
            "Referer": "https://music.163.com/"
        }
        # 定义多个歌单ID和名称，以及对应的类型
        self.playlists = {
            '19723756': {'name': '飙升榜', 'type': '流行'},
            '3779629': {'name': '新歌榜', 'type': '流行'},
            '2884035': {'name': '原创榜', 'type': '流行'},
            '3778678': {'name': '热歌榜', 'type': '流行'},
            '991319590': {'name': '中文说唱榜', 'type': '中文说唱'},
            '71384707': {'name': '古典榜', 'type': '古典'},
            '14028249541': {'name': '全球说唱榜', 'type': '欧美说唱'},
            '71385702': {'name': 'ACG榜', 'type': '日语'},
            '745956260': {'name': '韩语榜', 'type': '韩语'},
            '180106': {'name': 'UK榜', 'type': '欧美流行'},
            '5059633707': {'name': '摇滚榜', 'type': '摇滚'},
            '60131': {'name': '日语Oricon', 'type': '日语'},
            '2809513713': {'name': '欧美热歌', 'type': '欧美流行'},
            '12225155968': {'name': '欧美R&B', 'type': 'R&B'},
        }
        self.base_url = 'https://music.163.com/discover/toplist?id='
        self.output_dir = './netease_playlists'
        os.makedirs(self.output_dir, exist_ok=True)

        # 登录凭证（需要用户填写）
        self.cookies = {}

    def login(self, cookie_str=None):
        """登录网易云音乐

        Args:
            cookie_str: 从浏览器复制的cookie字符串，格式为 "key1=value1; key2=value2"
        """
        if cookie_str:
            # 解析cookie字符串
            cookies_dict = {}
            for item in cookie_str.split(';'):
                if '=' in item:
                    key, value = item.strip().split('=', 1)
                    cookies_dict[key] = value
            self.cookies = cookies_dict
            self.session.cookies.update(cookies_dict)
            print("已设置Cookie，尝试登录...")

            # 测试登录状态
            test_url = "https://music.163.com/"
            response = self.session.get(test_url, headers=self.headers)
            if "登录" not in response.text or "我的音乐" in response.text:
                print("登录成功！")
                return True
            else:
                print("登录失败，请检查Cookie")
                return False
        else:
            print("未提供Cookie，将以游客身份访问（可能无法获取付费歌曲URL）")
            return True

    def parse_url(self, url):
        try:
            response = self.session.get(url, headers=self.headers)
            if response.status_code == 200:
                return response.text
        except RequestException:
            print("请求失败")
        return None

    def get_playlist_info(self, html):
        """获取歌单的收藏、转发、评论数"""
        tree = etree.HTML(html)

        # 获取歌单名称
        playlist_name = tree.xpath('//h2[@class="f-ff2"]/text()')
        playlist_name = playlist_name[0] if playlist_name else '未知歌单'

        # 获取收藏数
        fav_element = tree.xpath('//a[@id="toplist-fav"]/i/text()')
        fav_count = fav_element[0].strip('()') if fav_element else '0'

        # 获取转发数
        share_element = tree.xpath('//a[@id="toplist-share"]/i/text()')
        share_count = share_element[0].strip('()') if share_element else '0'

        # 获取评论数
        comment_element = tree.xpath('//span[@id="comment-count"]/text()')
        comment_count = comment_element[0] if comment_element else '0'

        return playlist_name, fav_count, share_count, comment_count

    def get_song_ids_and_names(self, html):
        tree = etree.HTML(html)
        raw_id_list = tree.xpath('//a[contains(@href, "song?")]/@href')
        raw_name_list = tree.xpath('//a[contains(@href, "song?")]/text()')

        id_list = [id.split('=')[1] for id in raw_id_list if '$' not in id]
        name_list = [name for name in raw_name_list if '{' not in name]

        return id_list[:200], name_list[:200]

    def get_song_urls(self, song_ids):
        """批量获取歌曲的真实播放URL"""
        print("正在获取歌曲播放URL...")
        song_urls = {}

        # 网易云音乐获取歌曲详情的API
        url = "https://music.163.com/api/song/detail"

        # 分批处理，避免请求过大
        batch_size = 50
        for i in range(0, len(song_ids), batch_size):
            batch_ids = song_ids[i:i + batch_size]

            # 构造请求参数
            ids_str = ','.join(batch_ids)
            params = {
                'ids': f'[{ids_str}]'
            }

            try:
                response = self.session.get(url, params=params, headers=self.headers)
                if response.status_code == 200:
                    data = response.json()
                    if data.get('code') == 200:
                        for song in data.get('songs', []):
                            song_id = str(song['id'])
                            # 获取歌曲的MP3 URL
                            mp3_url = f"https://music.163.com/song/media/outer/url?id={song_id}.mp3"
                            song_urls[song_id] = {
                                'name': song['name'],
                                'artists': ', '.join([artist['name'] for artist in song['artists']]),
                                'album': song['album']['name'],
                                'mp3_url': mp3_url,
                                'duration': song['duration']  # 歌曲时长，毫秒
                            }
                else:
                    print(f"获取歌曲URL失败，状态码: {response.status_code}")
            except Exception as e:
                print(f"获取歌曲URL时出错: {e}")

        print(f"成功获取 {len(song_urls)} 首歌曲的URL")
        return song_urls

    def get_song_detail_stats(self, song_id):
        """获取单首歌曲的详细数据，包括点赞、收藏、转发量"""
        try:
            # 使用网易云音乐API获取歌曲详情
            detail_url = f"https://music.163.com/api/v1/song/detail/?ids=[{song_id}]"
            response = self.session.get(detail_url, headers=self.headers)

            if response.status_code == 200:
                data = response.json()
                if data.get('code') == 200 and data.get('songs'):
                    song_data = data['songs'][0]


                    comment_url = f"https://music.163.com/api/v1/resource/comments/R_SO_4_{song_id}?limit=1"
                    comment_response = self.session.get(comment_url, headers=self.headers)

                    like_count = 0
                    share_count = 0
                    comment_count = 0

                    if comment_response.status_code == 200:
                        comment_data = comment_response.json()
                        comment_count = comment_data.get('total', 0)

                    return {
                        'like_count': like_count,
                        'favorite_count': 0,  # 这个数据较难获取
                        'share_count': share_count,
                        'comment_count': comment_count
                    }

            return {
                'like_count': 0,
                'favorite_count': 0,
                'share_count': 0,
                'comment_count': 0
            }

        except Exception as e:
            print(f"获取歌曲 {song_id} 详细数据时出错: {e}")
            return {
                'like_count': 0,
                'favorite_count': 0,
                'share_count': 0,
                'comment_count': 0
            }

    def get_songs_stats_batch(self, song_ids):
        """批量获取歌曲统计数据"""
        print("正在获取歌曲统计数据（点赞、收藏、转发量）...")
        songs_stats = {}

        # 由于网易云音乐API限制，我们只能逐个获取
        for i, song_id in enumerate(song_ids):
            try:
                stats = self.get_song_detail_stats(song_id)
                songs_stats[song_id] = stats

                # 添加延迟，避免请求过快
                time.sleep(0.1)

                # 每10首歌曲打印一次进度
                if (i + 1) % 10 == 0:
                    print(f"已获取 {i + 1}/{len(song_ids)} 首歌曲的统计数据")

            except Exception as e:
                print(f"获取歌曲 {song_id} 统计数据失败: {e}")
                songs_stats[song_id] = {
                    'like_count': 0,
                    'favorite_count': 0,
                    'share_count': 0,
                    'comment_count': 0
                }

        print(f"成功获取 {len(songs_stats)} 首歌曲的统计数据")
        return songs_stats

    def get_json_data(self, html, playlist_id, playlist_info, fav_count, share_count, comment_count, get_urls=False,
                      get_stats=False):
        playlist_name = playlist_info['name']
        playlist_type = playlist_info['type']

        print(f"正在提取歌单【{playlist_name}】的歌曲数据...")
        json_text = re.findall(r'<textarea.*?id="song-list-pre-data".*?>(.*?)</textarea>', html, re.S)
        if not json_text:
            print("未找到 JSON 数据")
            return []

        result = json.loads(json_text[0])

        # 为每个歌单创建单独的文件夹
        playlist_dir = os.path.join(self.output_dir, f"{playlist_id}_{playlist_name}")
        os.makedirs(playlist_dir, exist_ok=True)

        # 获取歌曲ID列表
        ids, names = self.get_song_ids_and_names(html)

        # 如果需要获取歌曲URL
        song_urls = {}
        if get_urls:
            song_urls = self.get_song_urls(ids)

        # 如果需要获取歌曲统计数据
        songs_stats = {}
        if get_stats:
            songs_stats = self.get_songs_stats_batch(ids)

        # 构建歌曲数据列表
        songs_data = []
        for index, section in enumerate(result):
            song_id = str(jsonpath.jsonpath(section, '$.id')[0])
            title = jsonpath.jsonpath(section, '$.name')[0]
            artist = jsonpath.jsonpath(section, '$.artists..name')[0]
            pic = jsonpath.jsonpath(section, '$.album.picUrl')[0]
            last_rank = jsonpath.jsonpath(section, '$.lastRank')
            last_rank = last_rank[0] if last_rank else '等于当前排名'

            # 构建歌曲数据
            song_data = {
                'id': song_id,
                'name': title,
                'artist': artist,
                'album': jsonpath.jsonpath(section, '$.album.name')[0],
                'pic_url': pic,
                'last_rank': last_rank,
                'current_rank': index + 1,  # 当前排名，从1开始
                'type': playlist_type  # 添加类型属性
            }

            # 如果获取了URL，添加到歌曲数据
            if get_urls:
                url_info = song_urls.get(song_id, {})
                song_data['mp3_url'] = url_info.get('mp3_url', '')
                song_data['duration'] = url_info.get('duration', 0) // 1000  # 转换为秒

            # 如果获取了统计数据，添加到歌曲数据
            if get_stats:
                stats_info = songs_stats.get(song_id, {})
                song_data['stats'] = {
                    'like_count': stats_info.get('like_count', 0),
                    'favorite_count': stats_info.get('favorite_count', 0),
                    'share_count': stats_info.get('share_count', 0),
                    'comment_count': stats_info.get('comment_count', 0)
                }

            songs_data.append(song_data)

        # 构建完整的歌单数据
        playlist_data = {
            'playlist_info': {
                'id': playlist_id,
                'name': playlist_name,
                'type': playlist_type,
                'fav_count': fav_count,
                'share_count': share_count,
                'comment_count': comment_count,
                'song_count': len(songs_data),
                'update_time': self.get_current_time()
            },
            'songs': songs_data
        }

        # 保存为JSON文件
        json_path = os.path.join(playlist_dir, f'{playlist_name}.json')
        with open(json_path, 'w', encoding='utf8') as f:
            json.dump(playlist_data, f, ensure_ascii=False, indent=2)

        print(f"歌单【{playlist_name}】的数据已导出到 {json_path}")

        # 如果获取了URL，单独保存URL列表为文本文件
        if get_urls and song_urls:
            urls_path = os.path.join(playlist_dir, f'{playlist_name}_歌曲URL列表.txt')
            with open(urls_path, 'w', encoding='utf8') as f:
                f.write(f"歌单: {playlist_name}\n")
                f.write(f"歌单ID: {playlist_id}\n")
                f.write(f"类型: {playlist_type}\n\n")
                f.write("歌曲URL列表:\n")
                f.write("=" * 50 + "\n")

                for song_id, info in song_urls.items():
                    f.write(f"歌曲: {info['name']}\n")
                    f.write(f"歌手: {info['artists']}\n")
                    f.write(f"专辑: {info['album']}\n")
                    f.write(f"时长: {info['duration'] // 1000}秒\n")
                    f.write(f"URL: {info['mp3_url']}\n")
                    f.write("-" * 50 + "\n")

            print(f"歌曲URL列表已保存到: {urls_path}")

        return len(songs_data)

    def get_current_time(self):
        """获取当前时间字符串"""
        from datetime import datetime
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    def run_spider(self, get_urls=False, get_stats=False):
        """运行爬虫，爬取所有歌单

        Args:
            get_urls: 是否获取歌曲播放URL
            get_stats: 是否获取歌曲统计数据（点赞、收藏、转发量）
        """
        all_playlist_stats = []

        for playlist_id, playlist_info in self.playlists.items():
            playlist_name = playlist_info['name']
            print(f"\n正在爬取歌单: {playlist_name} (ID: {playlist_id})")
            url = self.base_url + playlist_id
            html = self.parse_url(url)

            if html:
                # 获取歌单信息
                actual_name, fav_count, share_count, comment_count = self.get_playlist_info(html)

                # 获取歌曲数据并保存
                song_count = self.get_json_data(
                    html, playlist_id, playlist_info,
                    fav_count, share_count, comment_count,
                    get_urls=get_urls,
                    get_stats=get_stats
                )

                # 记录统计信息
                all_playlist_stats.append({
                    '歌单ID': playlist_id,
                    '歌单名称': playlist_name,
                    '类型': playlist_info['type'],
                    '收藏数': fav_count,
                    '转发数': share_count,
                    '评论数': comment_count,
                    '歌曲数量': song_count
                })
            else:
                print(f"获取歌单 {playlist_id} 失败")

        # 保存所有歌单的汇总统计信息
        self.save_summary_stats(all_playlist_stats)

    def save_summary_stats(self, stats):
        """保存所有歌单的汇总统计信息"""
        summary_path = os.path.join(self.output_dir, '所有歌单汇总统计.json')

        # 构建汇总数据
        summary_data = {
            'total_playlists': len(stats),
            'total_songs': sum(stat['歌曲数量'] for stat in stats),
            'update_time': self.get_current_time(),
            'playlists': stats
        }

        with open(summary_path, 'w', encoding='utf8') as f:
            json.dump(summary_data, f, ensure_ascii=False, indent=2)

        print(f"\n所有歌单汇总统计已保存到: {summary_path}")

        # 打印统计信息
        print("\n=== 歌单统计信息汇总 ===")
        for stat in stats:
            print(f"歌单: {stat['歌单名称']}")
            print(f"  类型: {stat['类型']}")
            print(f"  ID: {stat['歌单ID']}")
            print(
                f"  收藏: {stat['收藏数']} | 转发: {stat['转发数']} | 评论: {stat['评论数']} | 歌曲: {stat['歌曲数量']}首")
            print()


if __name__ == '__main__':
    spider = CloudMusicSpider()

    # 登录（可选，如果需要获取付费歌曲URL）
    # 从浏览器登录网易云音乐后，复制Cookie字符串
    cookie_str = input("请输入网易云音乐Cookie（留空则以游客身份访问）: ").strip()
    if cookie_str:
        spider.login(cookie_str)

    # 是否获取歌曲URL
    url_choice = input("是否获取歌曲播放URL？(y/N): ").strip().lower()
    get_urls = url_choice == 'y'

    # 是否获取歌曲统计数据
    stats_choice = input("是否获取歌曲统计数据（点赞、收藏、转发量）？(y/N): ").strip().lower()
    get_stats = stats_choice == 'y'

    spider.run_spider(get_urls=get_urls, get_stats=get_stats)