from vidfetch.api.huggingface import push_file_to_hf

if __name__ == '__main__':
    hf_token = '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'
    hf_repo_id = 'OpenVideo/YouTube-Commons-5G-Raw'
    file_path = '/mnt/application/test.mp4'
    path_in_repo = 'test.mp4'
    push_file_to_hf(hf_token, hf_repo_id, file_path, path_in_repo)

