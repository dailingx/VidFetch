import os
os.system('pip uninstall vidfetch -y')
os.system('pip install -U https://github.com/dailingx/VidFetch/archive/master.zip')
os.system('pip install --upgrade google-api-python-client')
os.system('pip install pandas')
os.system('pip install -U https://huggingface.co/dailingx/youtube-dl-package/resolve/main/youtube-dl-2024.04.08.tar.gz')
# os.system('wget https://yt-dl.org/downloads/latest/youtube-dl -O /usr/local/bin/youtube-dl')
# os.system('chmod a+rx /usr/local/bin/youtube-dl')

import sys
import gradio as gr
from vidfetch.website.youtube import YoutubeVideoDataset
import pandas as pd
from pandas.api.types import is_numeric_dtype


def fetch(
    kw_file,
    dev_key: str,
    hf_token: str,
    hf_ds_repo_id: str,
    key_word: str = None
):
    df = pd.read_csv(kw_file.name)
    if len(df['keyword']) <= 0:
        return 'no keyword'

    success_kw = ''
    for index, value in df['keyword'].items():
        if 'num' in df.columns:
            video_max_num = df['num'][index]
        else:
            video_max_num = 50

        youtube_video_dataset = YoutubeVideoDataset(
            root_dir="./",
            google_cloud_developer_key=dev_key,
            search_keyword=value,
            video_max_num=video_max_num,
            hf_token=hf_token,
            hf_ds_repo_id=hf_ds_repo_id
        )
        youtube_video_dataset.download()

        success_kw = success_kw + value
    return success_kw


with gr.Blocks() as demo:
    gr.Markdown('''OpenVideo Youtube fetch demo''')
    with gr.Row():
        with gr.Column():
            # kw_input_text = gr.Text(label='Keyword')
            kw_input_file = gr.File(label="Upload CSV File, Include Columns: keyword, num, ...")
            dev_key_input_text = gr.Text(label='Google Cloud Developer Key')
            hf_token_input_text = gr.Text(label='HF Token')
            hf_ds_repo_id_text = gr.Text(label='HF Dataset Repo ID, like: OpenVideo/YouTube-Commons-5G-Raw')
            fetch_btn = gr.Button("Fetch")
        result = gr.Text()

    fetch_btn.click(fn=fetch, inputs=[kw_input_file, dev_key_input_text, hf_token_input_text, hf_ds_repo_id_text],
                    outputs=[result])


if __name__ == "__main__":
    demo.queue(max_size=1)
    demo.launch(share=False, max_threads=1)
