from vidfetch.website.youtube import YoutubeVideoDataset
import argparse


def get_parser():
    parser = argparse.ArgumentParser()
    parser.add_argument("--root_dir", type=str)
    parser.add_argument("--google_cloud_developer_key", type=str)
    parser.add_argument("--search_keyword", type=str)
    parser.add_argument("--video_max_num", type=int)
    parser.add_argument("--hf_token", type=str)
    parser.add_argument("--hf_ds_repo_id", type=str)
    return parser


if __name__ == '__main__':
    parser = get_parser()
    args = parser.parse_args()
    youtube_video_dataset = YoutubeVideoDataset(
        root_dir=args.root_dir,
        google_cloud_developer_key=args.google_cloud_developer_key,
        search_keyword=args.search_keyword,
        video_max_num=args.video_max_num,
        hf_token=args.hf_token,
        hf_ds_repo_id=args.hf_ds_repo_id
    )

    youtube_video_dataset.download()