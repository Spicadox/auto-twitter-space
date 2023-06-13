from urllib import error
import subprocess
import requests
from requests.adapters import HTTPAdapter, MaxRetryError
from urllib3 import Retry
import const
import discord
from log import create_logger
import os
import re
import time


# Function takes in the file name and check if it contains illegal characters
# If it contains an illegal character then remove it and return the new file name without the illegal character
def checkFileName(fileName):
    invalidName = re.compile(r"[\\*?<>:\"/\|]")
    newFileName = fileName
    if re.search(invalidName, fileName) is not None:
        newFileName = re.sub(invalidName, "_", fileName)
    # If file name has multiple lines then join them together(because stripping newline doesn't work)
    if "\n" in fileName:
        title_array = fileName.splitlines()
        newFileName = " ".join(title_array)
    return newFileName


def send_file(file_path, space_id, twitter_name, space_title, space_date):
    logger = create_logger("logfile_twspace.log")
    if os.path.isfile(file_path):
        webhook = discord.Webhook.from_url(const.WEBHOOK_DOWNLOAD_URL, adapter=discord.RequestsWebhookAdapter())
        space_file = discord.File(file_path)
        content = f"The twitter space for {twitter_name} was downloaded\n`[{space_date}] {twitter_name} - {space_title} ({space_id})`"
        try:
            webhook.send(content=content, file=space_file)
        except discord.HTTPException as e:
            logger.error(e.text, exc_info=True)
    else:
        logger.error("Could not find space file to send", exc_info=True)


def get_m3u8_chunk(base_url, master_url, logger, session):
    # Get the playlist m3u8
    t = session.get(master_url).content.decode('utf-8')
    # logger.debug(t)
    master_playlist = re.findall(".*m3u8$", t, re.MULTILINE)
    for i in master_playlist:
        master_playlist = i
    logger.debug(master_playlist)
    # Get the playlist m3u8 content and replace the chunk url with the appropriate prefix
    chunk_m3u8 = base_url + master_playlist
    logger.debug(chunk_m3u8)
    return chunk_m3u8


def correct_duration(t, duration, logger):
    if duration is None:
        return True
    moe = 30
    reg = re.compile("#EXTINF:(\d.\d{3})")
    result = re.findall(reg, t)
    m3u8_duration = sum(map(float, result))
    logger.debug(f"Space duration: {duration - moe} <= {m3u8_duration} <= {duration + moe}")
    if duration - moe <= m3u8_duration <= duration + moe:
        return True
    else:
        return False


def download(m3u8_id, rest_id, space_creator, handle_name, space_title, space_server, space_duration, space_date, logger=None):
    session = requests.Session()
    retry = Retry(total=5, connect=5, backoff_factor=1, status_forcelist=[400, 401, 403, 404, 429, 500, 502, 503, 504])
    session.mount("https://", HTTPAdapter(max_retries=retry))
    if logger is None:
        logger = create_logger("logfile.log")
    DOWNLOAD_PATH = os.path.join(const.DOWNLOAD, space_creator)
    SEND_DOWNLOAD = const.SEND_DOWNLOAD
    if DOWNLOAD_PATH == "True":
        DOWNLOAD_PATH = os.path.join(os.getcwd(), space_creator)
    elif not os.path.exists(DOWNLOAD_PATH):
        os.makedirs(DOWNLOAD_PATH)

    deployment_server, periscope_server = space_server

    base_url = f'https://{deployment_server}-{periscope_server}.pscp.tv'
    base_addon = '/Transcoding/v1/hls/'

    file_name = checkFileName(space_title)

    # Remove .video from the periscope_server string
    periscope_server = periscope_server.removesuffix('.video')
    end_masterurl = "/non_transcode/us-east-1/periscope-replay-direct-prod-us-east-1-public/audio-space/master_playlist.m3u8"
    end_chunkurl = f'/non_transcode/{periscope_server}/periscope-replay-direct-prod-{periscope_server}-public/audio-space/chunk'
    master_url = base_url+base_addon+m3u8_id+end_masterurl
    logger.debug(master_url)

    # Retry on 404 error
    retry = 0
    MAX_RETRY = 20
    while retry < MAX_RETRY:
        try:
            # Get the chunk m3u8
            chunk_m3u8 = get_m3u8_chunk(base_url, master_url, logger, session)
            t = session.get(chunk_m3u8).content.decode('utf-8')
            if not correct_duration(t, space_duration, logger):
                # raise error.HTTPError(url=chunk_m3u8, code=102, msg="M3U8 is incomplete", hdrs=None, fp=None)
                retry += 1
                logger.warning(f"Incorrect duration, M3U8 playlist download retry({retry}/{MAX_RETRY}) ...{' ' * 10}")
                logger.debug(chunk_m3u8)
                time.sleep(const.SLEEP_TIME)
                continue
            break
        except (MaxRetryError, requests.exceptions.RetryError, requests.exceptions.ConnectionError) as retryError:
            retry += 1
            logger.debug(retryError, exc_info=True)
            logger.warning(f"Retrying({retry}/{MAX_RETRY}) m3u8 playlist download...{' ' * 10}")
            time.sleep(const.SLEEP_TIME)
        except error.HTTPError as httpError:
            retry += 1
            logger.debug(httpError, exc_info=True)
            logger.warning(f"Retrying({retry}/{MAX_RETRY}) m3u8 playlist download...{' '*10}")
            time.sleep(const.SLEEP_TIME)
        except Exception as e:
            retry += 1
            logger.error(e, exc_info=True)
            logger.warning(f"Retrying({retry}/{MAX_RETRY}) m3u8 playlist download...{' ' * 10}")
            time.sleep(const.SLEEP_TIME)
    t = t.replace('chunk', base_url+base_addon+m3u8_id+end_chunkurl)
    logger.debug(t)
    filename = f'{rest_id}.m3u8'
    output = f'{DOWNLOAD_PATH}\\{space_date} - {space_creator} - {file_name} ({rest_id}).m4a'
    command = ['ffmpeg', '-n', '-loglevel', 'info', '-protocol_whitelist', 'file,crypto,https,tcp,tls']
    command += ['-i', filename, '-metadata', f'date={space_date}']
    command += ['-metadata', f'comment=feat.{handle_name}'] if space_creator != handle_name else ['-metadata', f'comment={master_url}']
    command += ['-metadata', f'artist={space_creator}', '-metadata', f'title={space_title}', '-c', 'copy', output]

    # Check if the file already exist and if it does remove it
    try:
        if os.path.isfile(filename):
            os.remove(filename)
    except PermissionError as perm_error:
        logger.error(perm_error, exc_info=True)
    try:
        # Create a new file with the appropriately replaced chunk url
        with open(filename, 'w') as f:
            f.write(t)

        download_result = subprocess.run(command, capture_output=True, text=True)
        logger.debug(download_result.stderr)

        if SEND_DOWNLOAD:
            send_file(output, rest_id, space_creator, space_title, space_date)
        if retry >= MAX_RETRY:
            logger.warning(f"Download completed for {rest_id}, but may not be completely downloaded")
        else:
            logger.info(f"Download completed for {rest_id + ' ' * 10}")
    except Exception:
        logger.error(exc_info=True)
    finally:
        # Check if the file already exist and if it does remove it
        try:
            if os.path.isfile(filename):
                os.remove(filename)
        except PermissionError as perm_error:
            logger.error(perm_error, exc_info=True)
    return True


if __name__ == "__main__":
    import threading

    def loading_text():
        loading_string = f"[INFO] Downloading twitter space {space_id} "
        animation = ["     ", ".    ", "..   ", "...  ", ".... ", "....."]
        idx = 0
        while status:
            print(loading_string + animation[idx % len(animation)], end="\r")
            time.sleep(0.3)
            idx += 1
            if idx == 6:
                idx = 0

    def get_space_server(m3u8_url):
        reg_result = re.search("(https:\/\/)((?:[^-]*-){2})(.*)(\.pscp.*)", m3u8_url)
        # regex will return something like 'prod-fastly-' so remove the last dash
        deployment_server = reg_result.group(2)[:-1]
        periscope_server = reg_result.group(3)
        server = (deployment_server, periscope_server)
        return server

    try:
        status = True
        m3u8_url = input("m3u8 Url: ")
        space_id = input("space id: ")
        twitter_name = input("twitter name: ")
        space_title = input("space title: ")
        space_date = input("space date(YYYYMMDD): ")
        # space_date = datetime.strptime(space_date, "%Y%m%d").timestamp() * 1000
        m3u8_id = re.search("(.*\/Transcoding\/v1\/hls\/(.*)(\/non_transcode.*))", m3u8_url).group(2)
        server = get_space_server(m3u8_url)
        # m3u8_id, rest_id, space_creator_name, handle_name, space_title, space_server, space_duration, space_date, logger=None
        t1 = threading.Thread(target=loading_text)
        t1.start()
        download(m3u8_id=m3u8_id, rest_id=space_id, space_creator=twitter_name, handle_name=twitter_name, space_title=space_title,
                 space_server=server, space_duration=None, space_date=space_date)
        status = False
        input("Download complete, press any key to exit...")
        exit()
    except Exception as e:
        print(f"\rError encountered...{' '*40}\n{e}")
        while True:
            input("Exit...")
            exit()
