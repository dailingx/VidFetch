import os
os.system('pip install huggingface_hub')


import time
import shutil
from huggingface_hub import HfApi
import gradio as gr

CACHE_DIR = "hf2ms_cache"
LOCAL_DIR = "hf2ms_local"
USERNAME = "dailingx"
EMAIL = "468551414@qq.com"


def clone_from_ms(
        ms_token: str,
        ms_repo_id: str,
        clone_dir: str
):
    if os.path.exists(clone_dir):
        ori_dir = os.getcwd()
        os.chdir(clone_dir)
        os.system("GIT_LFS_SKIP_SMUDGE=1 git pull")
        os.chdir(ori_dir)
        message = f"the repo already exists, so just pull successfully!"
    command = f"GIT_LFS_SKIP_SMUDGE=1 git clone https://oauth2:{ms_token}@www.modelscope.cn/datasets/{ms_repo_id}.git"
    os.system(command)
    configuration_path = os.path.join(clone_dir, "configuration.json")
    if not os.path.exists(configuration_path):
        open(configuration_path, "w").close()
    # message
    message = f"clone from https://oauth2:{ms_token}@www.modelscope.cn/datasets/{ms_repo_id}.git successfully!"
    return message


def hf_list_repo_files(
        hf_token: str,
        hf_repo_id: str,
        repo_type: str = "dataset"
):
    hf_api = HfApi(token=hf_token)
    files = hf_api.list_repo_files(repo_id=hf_repo_id, repo_type=repo_type)
    return files


def pull_from_hf(
        hf_token: str,
        hf_repo_id: str,
        filename: str,
):
    if not hf_repo_id:
        raise gr.Error("Please enter the repo_id of huggingface")
    if not filename:
        raise gr.Error("Please enter the filename")

    if "," in filename:
        filename_list = filename.split(",")
        for _filename in filename_list:
            save_path = os.path.join(LOCAL_DIR, _filename)
            if os.path.exists(save_path):
                message = "the file already exists!"
                return message

            # download
            hf_api = HfApi(token=hf_token)
            hf_api.hf_hub_download(
                repo_id=hf_repo_id,
                repo_type="dataset",
                filename=_filename,
                cache_dir=CACHE_DIR,
                local_dir=LOCAL_DIR,
                local_dir_use_symlinks=False
            )
    else:
        save_path = os.path.join(LOCAL_DIR, filename)
        if os.path.exists(save_path):
            message = "the file already exists!"
            return message

        # download
        hf_api = HfApi(token=hf_token)
        hf_api.hf_hub_download(
            repo_id=hf_repo_id,
            repo_type="dataset",
            filename=filename,
            cache_dir=CACHE_DIR,
            local_dir=LOCAL_DIR,
            local_dir_use_symlinks=False
        )

    # message
    message = f"Pull from https://huggingface.co/datasets/{hf_repo_id} successfully!"
    print(message)
    return message


def move_file_from_local_to_clone_dir(
        filename: str,
        clone_dir: str
):
    # move to the clone dir
    if "," in filename:
        filename_list = filename.split(",")
        for _filename in filename_list:
            if "/" in _filename:
                dirname = os.path.dirname(_filename)
                src_dir = os.path.join(clone_dir, dirname)
                if not os.path.exists(src_dir):
                    os.makedirs(src_dir)
            src = os.path.join(LOCAL_DIR, _filename)
            dst = os.path.join(clone_dir, _filename)
            shutil.move(src=src, dst=dst)
    else:
        if "/" in filename:
            dirname = os.path.dirname(filename)
            src_dir = os.path.join(clone_dir, dirname)
            if not os.path.exists(src_dir):
                os.makedirs(src_dir)
        src = os.path.join(LOCAL_DIR, filename)
        dst = os.path.join(clone_dir, filename)
        shutil.move(src=src, dst=dst)

    # message
    message = f"move the file from {src} to {dst} successfully!"
    print(message)
    return message


def push_to_ms(
        username: str,
        email: str,
        ms_repo_id: str,
        clone_dir: str,
        filename: str
):
    # push to ms
    ori_dir = os.getcwd()
    os.chdir(clone_dir)
    os.system("apt-get install git-lfs")
    os.system("git lfs install")
    os.system(f"git config --global user.email {email}")
    os.system(f"git config --global user.name {username}")
    if "," in filename:
        filename_list = filename.split(",")
        num = len(filename_list)
        for _filename in filename_list:
            os.system(f"git lfs track '{_filename}'")
        os.system("git add .")
        os.system(f"git commit -m 'upload {num} files'")
        os.system(f"git push")
        os.chdir(ori_dir)
    else:
        os.system(f"git lfs track '{filename}'")
        os.system("git add .")
        os.system(f"git commit -m 'upload {filename}'")
        os.system(f"git push")
        os.chdir(ori_dir)
    # remove clone dir
    if os.path.exists(clone_dir):
        shutil.rmtree(clone_dir)
    message = f'Pushed to https://www.modelscope.cn/datasets/{ms_repo_id} successfully!'
    print(message)
    return message


def handle(
        hf_token: str,
        ms_token: str,
        repo_type: str,
        hf_repo: str,
        ms_repo: str,
):
    clone_dir = ms_repo.split("/")[-1]
    hf_file_list = hf_list_repo_files(hf_token, hf_repo, repo_type)
    print(f"all file in hf: {hf_file_list}")

    for filename in hf_file_list:
        clone_from_ms(ms_token, ms_repo, clone_dir)
        time.sleep(1)
        pull_from_hf(hf_token, hf_repo, filename)
        time.sleep(1)
        move_file_from_local_to_clone_dir(filename, clone_dir)
        time.sleep(1)
        push_to_ms(USERNAME, EMAIL, ms_repo, clone_dir, filename)
        time.sleep(10)


with gr.Blocks() as demo:
    gr.Markdown(
        '''
        This space uploads model from Huggingface to ModelScope.
        **Please make sure that you're the owner of the repo or have permission from the owner to do so!**
        # How to use this Space?
        - Duplicate this Space and providing MS token (optional) and your read/write HF token (mandatory)
        - Create your target model repo on HF. This step needs to be done manually. The Space doesn't do create an empty repo for you.
        - In your own private Space, fill in information below.
        - Click submit then watch for output in container log for progress.
        - Create README.md file (since the metadata is not compatible with HF)
        '''
    )
    hf_token = gr.Textbox(label="HuggingFace Token")
    ms_token = gr.Textbox(label="ModelScope Git Token")
    repo_type = gr.Textbox(label="Repo Type", value="dataset")
    hf_repo = gr.Textbox(label="HuggingFace Repo")
    ms_repo = gr.Textbox(label="ModelScope Repo")

    # username = gr.Textbox(label="ModelScope username")
    # email = gr.Textbox(label="ModelScope email")
    # hf_repo_id = gr.Textbox(label="HF Model Repo ID (case sensitive). \nPlease make sure that this model has already been created")
    # ms_repo_id = gr.Textbox(label="Target Model Scope Repo ID (case sensitive) \nPlease make sure that this model has already been created")
    # filename = gr.Textbox(label="the path of the file")

    with gr.Row():
        button = gr.Button("Submit", variant="primary")
        clear = gr.Button("Clear")

    button.click(
        handle,
        [hf_token, ms_token, repo_type, hf_repo, ms_repo],
        outputs=None
    )

if __name__ == "__main__":
    demo.queue(max_size=1)
    demo.launch(share=False, max_threads=1)