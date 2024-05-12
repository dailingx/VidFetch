import os
import shutil
import traceback
from vidfetch.video import VideoDataset, VideoData
from vidfetch.utils import download, get_md5
from apiclient.discovery import build
import subprocess
import time
import datetime
from vidfetch.api.huggingface import push_file_to_hf
import tarfile


class YoutubeVideoDataset(VideoDataset):
    def __init__(self, root_dir: str, google_cloud_developer_key: str, search_keyword: str, hf_token: str, hf_ds_repo_id: str,
                 start_page_token: str = None, video_max_num: int = 1000000):
        super().__init__(
            website="youtube",
            root_dir=root_dir,
        )
        self.search_keyword = search_keyword
        self.start_page_token = start_page_token
        self.video_max_num = video_max_num
        self.cur_fetch_video_num = 0
        self.hf_token = hf_token
        self.hf_ds_repo_id = hf_ds_repo_id

        os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"
        api_service_name = "youtube"
        api_version = "v3"
        self.youtube_api_client = build(api_service_name, api_version, developerKey=google_cloud_developer_key)

    def download(
            self,
            platform: str = "windows",
            restart: bool = False
    ):
        print(f'begin to do download, search_keyword: {self.search_keyword}, video_max_num: {self.video_max_num}, time: {datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")}')
        start_time = time.time()

        last_video_info = self.monitor.last_video
        if last_video_info == dict():
            restart = True

        if restart:
            start_page_token = self.start_page_token
            page_start_idx = 0
        else:
            start_page_token = last_video_info.get('last_page_token', None)
            page_start_idx = last_video_info.get('last_page_start_idx', 0)
            self.cur_fetch_video_num = last_video_info.get('last_fetch_video_num', 0)
            message = f"Starting from page: {start_page_token}, page_start_idx: {page_start_idx}..."
            print(message)

        page_token = start_page_token
        while page_token != "last_page":
            if self.cur_fetch_video_num >= self.video_max_num:
                print(f"youtube dataset has fetch {self.cur_fetch_video_num} videos, done!")
                return

            video_meta = self.fetch_video_meta_with_api(self.search_keyword, page_token)
            print(f"search_keyword: {self.search_keyword}, page_token: {page_token}, video_meta: {video_meta}")
            video_ids = video_meta["video_ids"]
            if video_ids is None or len(video_ids) == 0:
                break

            try:
                self.download_with_video_ids(video_ids, page_token, page_start_idx)
                # reset page_start_idx
                if page_start_idx != 0:
                    page_start_idx = 0
            except Exception as e:
                print(f"download_with_video_ids error, search_keyword: {self.search_keyword}, page_token: {page_token}")
                error_message = traceback.format_exc()
                self.log_error(error_message)

            # update page_token for next page
            if video_meta["next_page_token"] is None:
                page_token = "last_page"
            else:
                page_token = video_meta["next_page_token"]

        print(
            f"video download success, search_keyword: {self.search_keyword}, fetch_video_num: {self.cur_fetch_video_num}, "
            f"time: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}, cost: {(time.time() - start_time)}s")
        self.compress_upload_hf()
        print(f"video compress and upload to hf success, search_keyword: {self.search_keyword}, fetch_video_num: {self.cur_fetch_video_num}, "
              f"time: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}, all-cost: {(time.time()-start_time)}s")


    def fetch_video_meta_with_api(self,
                                  keyword: str,
                                  page_token):
        # youtube data api: https://developers.google.com/youtube/v3/docs/videos/list?hl=zh-cn#usage
        request = self.youtube_api_client.search().list(
            q=keyword,
            type="video",
            part="id,snippet",
            videoLicense="creativeCommon",
            pageToken=page_token,
            # order="date",
            maxResults=50
        )
        response = request.execute()

        # get video info
        next_page_token = response.get("nextPageToken")
        video_ids = []
        for search_result in response.get("items", []):
            if search_result["id"]["kind"] == "youtube#video":
                video_ids.append(search_result["id"]["videoId"])
        video_meta = {"next_page_token": next_page_token, "video_ids": video_ids}
        return video_meta


    def download_with_video_ids(
            self,
            video_ids: [],
            page_token: str,
            start_idx: int
    ):
        if start_idx > 0:
            start_idx = start_idx - 1
        for idx, video_id in enumerate(video_ids[start_idx:], start=start_idx):
            if self.cur_fetch_video_num >= self.video_max_num:
                print(f"youtube dataset has fetch {self.cur_fetch_video_num} videos, done!")
                return

            try:
                self.download_video(video_id, page_token, idx)
            except Exception as e:
                print(f"download_video error, search_keyword: {self.search_keyword}, page_token: {page_token}, idx: {idx}, video_id: {video_id}")
                error_message = traceback.format_exc()
                self.log_error(error_message)


    def download_video(
            self,
            video_id: str,
            page_token: str,
            idx: int
    ):
        youtube_base_url = "https://www.youtube.com/watch?v="
        download_url = youtube_base_url + video_id

        # check if is downloaded sucessfully
        # if download_url in self.monitor.downloaded_url_list:
        #     return

        # download
        tmp_filename = f"youtube_{self.search_keyword.replace(' ', '_')}_{page_token}_{str(idx)}_{video_id}_tmp.mp4"
        tmp_download_path = os.path.join(self.tmp_dir, tmp_filename)
        download_success = self.download_one_instance(
            download_url=download_url,
            download_path=tmp_download_path
        )
        if not download_success:
            error_message = f"error occurred when the download url is {download_url}"
            self.log_error(error_message)
            self.clear_tmpfile(tmp_download_path)
            return

        # md5 = get_md5(tmp_download_path)
        save_path = os.path.join(self.download_dir, f"{video_id}.mp4")
        shutil.move(tmp_download_path, save_path)

        self.cur_fetch_video_num = self.cur_fetch_video_num + 1
        video_info_dict = {
            # "md5": md5,
            "uid": video_id,
            "free": True,
            "save_path": save_path,
            "website": self.website,
            "download_url": download_url,
            "last_page_token": page_token,
            "last_page_start_idx": idx,
            "last_fetch_video_num": self.cur_fetch_video_num
        }

        video_data = VideoData(
            video_info_dict=video_info_dict,
            basic_info_include=False
        )
        new_video_info_dict = video_data.get_video_info_dict()
        self.monitor.add_item_v2(new_video_info_dict)
        self.monitor.update_state()
        self.monitor.save_state_dict()

    def clear_tmpfile(self, tmp_download_path: str):
        if os.path.exists(tmp_download_path):
            os.remove(tmp_download_path)

    def download_one_instance(
            self,
            download_url: str,
            download_path: str
    ):
        download_success = True
        command = ['youtube-dl', '-o', download_path, download_url]
        try:
            subprocess.run(command)
            print(f"download_one_instance success, command: {command}")
        except:
            download_success = False
            error_message = f"error occurred when the download url is {download_url}"
            self.log_error(error_message)
        return download_success


    def compress_upload_hf(self):
        output_filename = self.search_keyword + '.tar.gz'
        with tarfile.open(output_filename, "w:gz") as tar:
            tar.add(self.download_dir, arcname=os.path.basename(self.download_dir))

        file_path = os.path.join(self.download_dir, output_filename)
        path_in_repo = output_filename
        push_file_to_hf(self.hf_token, self.hf_ds_repo_id, file_path, path_in_repo)

        os.remove(self.download_dir)

