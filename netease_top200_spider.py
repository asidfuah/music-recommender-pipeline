import os
import requests
import json
import jsonpath
import re
import csv
from lxml import etree
from requests.exceptions import RequestException


class CloudMusicSpider:
    def __init__(self):
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                          "AppleWebKit/537.36 (KHTML, like Gecko) "
                          "Chrome/85.0.4183.121 Safari/537.36"
        }
        self.url = 'https://music.163.com/discover/toplist?id=60198'
        self.base_music_url = 'http://music.163.com/song/media/outer/url?id='
        self.output_dir = './netease_top200'
        os.makedirs(self.output_dir, exist_ok=True)

    def parse_url(self, url):
        try:
            response = requests.get(url, headers=self.headers)
            if response.status_code == 200:
                return response.text
        except RequestException:
            print("请求失败")
        return None

    def get_song_ids_and_names(self, html):
        tree = etree.HTML(html)
        raw_id_list = tree.xpath('//a[contains(@href, "song?")]/@href')
        raw_name_list = tree.xpath('//a[contains(@href, "song?")]/text()')

        id_list = [id.split('=')[1] for id in raw_id_list if '$' not in id]
        name_list = [name for name in raw_name_list if '{' not in name]

        return id_list[:200], name_list[:200]

    def get_json_data(self, html):
        print("正在提取歌曲数据并导出为 CSV...")
        json_text = re.findall(r'<textarea.*?id="song-list-pre-data".*?>(.*?)</textarea>', html, re.S)
        if not json_text:
            print("未找到 JSON 数据")
            return []

        result = json.loads(json_text[0])
        csv_path = os.path.join(self.output_dir, '网易云音乐Top200.csv')

        with open(csv_path, 'w', newline='', encoding='utf8') as f:
            writer = csv.writer(f)
            writer.writerow(['歌名', '歌手', '图片链接', '上次排名', '类型'])

            for section in result:
                title = jsonpath.jsonpath(section, '$.name')[0]
                artist = jsonpath.jsonpath(section, '$.artists..name')[0]
                pic = jsonpath.jsonpath(section, '$.album.picUrl')[0]
                last_rank = jsonpath.jsonpath(section, '$.lastRank')
                last_rank = last_rank[0] if last_rank else '等于当前排名'
                writer.writerow([title, artist, pic, last_rank, '电音'])

        print(f"歌曲信息已导出到 {csv_path}")

    def download_songs(self, ids, names):
        print("开始下载歌曲...")
        for music_id, music_name in zip(ids, names):
            try:
                music_url = self.base_music_url + music_id
                response = requests.get(music_url, headers=self.headers, timeout=10)

                # 文件名清理
                safe_name = re.sub(r'[\\/*?:"<>|]', '_', music_name)
                file_path = os.path.join(self.output_dir, f"{safe_name}.mp3")

                with open(file_path, 'wb') as f:
                    f.write(response.content)
                print(f"《{music_name}》下载成功")
            except Exception as e:
                print(f"下载失败: {music_name}, 错误信息: {e}")

    def run_spider(self):
        html = self.parse_url(self.url)
        if html:
            ids, names = self.get_song_ids_and_names(html)
            self.get_json_data(html)
            self.download_songs(ids, names)
        else:
            print("获取网页失败，爬虫终止")


if __name__ == '__main__':
    spider = CloudMusicSpider()
    spider.run_spider()