import requests


def load_json_url(url):
    return requests.get(url).json()


def download_file(self, url, local_file_path):
    r = requests.get(url, stream=True)
    r.raise_for_status()

    with open(local_file_path, 'wb') as f:
        for chunk in r.iter_content(chunk_size=1024):
            if chunk:   # filter out keep-alive new chunks
                f.write(chunk)
