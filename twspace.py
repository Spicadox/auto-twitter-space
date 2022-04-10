import time
import urllib.request
from urllib import error
import re
import subprocess
import const
import discord
from log import create_logger
import os


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
            print(" "*50, end="\r")
            logger.error(e.text, exc_info=True)
    else:
        print("", end="\r")
        logger.error("Could not find space file to send", exc_info=True)


def get_m3u8_chunk(base_url, master_url, logger):
    # Get the playlist m3u8
    t = urllib.request.urlopen(master_url).read().decode('utf-8')
    # logger.debug(t)
    master_playlist = re.findall(".*m3u8$", t, re.MULTILINE)
    for i in master_playlist:
        master_playlist = i
    logger.debug(master_playlist)
    # Get the playlist m3u8 content and replace the chunk url with the appropriate prefix
    chunk_m3u8 = base_url + master_playlist
    logger.debug(chunk_m3u8)
    return chunk_m3u8


def download(m3u8_id, space_id, twitter_name, space_title, space_date, server):
    logger = create_logger("logfile.log")
    DOWNLOAD_PATH = const.DOWNLOAD
    SEND_DOWNLOAD = const.SEND_DOWNLOAD
    if DOWNLOAD_PATH == "True":
        DOWNLOAD_PATH = os.getcwd()
    elif not os.path.exists(DOWNLOAD_PATH):
        os.makedirs(DOWNLOAD_PATH)

    deployment_server = server[0]
    periscope_server = server[1]

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
    time.sleep(60)
    retry = 0
    MAX_RETRY = 10
    while retry <= MAX_RETRY:
        try:
            # Get the chunk m3u8
            chunk_m3u8 = get_m3u8_chunk(base_url, master_url, logger)
            t = urllib.request.urlopen(chunk_m3u8).read().decode('utf-8')
            break
        except error.HTTPError as httpError:
            retry += 1
            print("", end="\r")
            logger.error(httpError, exc_info=True)
            logger.info(f"Retrying(attempt {retry}/{MAX_RETRY}) m3u8 playlist download in {const.SLEEP_TIME} secs...")
            time.sleep(const.SLEEP_TIME)
    if retry == 10:
        print("", end="\r")
        logger.info(f"Download for {twitter_name}'s {space_id} failed...")
        return True
    t = t.replace('chunk', base_url+base_addon+m3u8_id+end_chunkurl)
    logger.debug(t)
    filename = f'{space_id}.m3u8'
    output = f'{DOWNLOAD_PATH}\\{space_date} - {twitter_name} - {file_name} ({space_id}).m4a'
    command = ['ffmpeg', '-n', '-loglevel', 'info', '-protocol_whitelist', 'file,crypto,https,tcp,tls']
    command += ['-i', filename, '-metadata', f'date={space_date}', '-metadata', f'comment={m3u8_id}']
    command += ['-metadata', f'artist={twitter_name}', '-metadata', f'title={space_title}', '-c', 'copy', output]

    # Check if the file already exist and if it does remove it
    if os.path.isfile(filename):
        os.remove(filename)
    try:
        # Create a new file with the appropriately replaced chunk url
        with open(filename, 'w') as f:
            f.write(t)

        download_result = subprocess.run(command, capture_output=True, text=True)
        logger.debug(download_result.stderr)

        if SEND_DOWNLOAD:
            send_file(output, space_id, twitter_name, space_title, space_date)
        print("", end="\r")
        logger.info(f"Download completed for {space_id}")
    except Exception:
        print("", end="\r")
        logger.error(exc_info=True)
    finally:
        # Check if the file already exist and if it does remove it
        if os.path.isfile(filename):
            os.remove(filename)

    return True


if __name__ == "__main__":
    import twitter_space_bot
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

    try:
        status = True
        m3u8_url = input("m3u8 Url: ")
        m3u8_id = twitter_space_bot.get_m3u8_id(m3u8_url)
        server = twitter_space_bot.get_server(m3u8_url)
        space_id = input("space id: ")
        twitter_name = input("twitter name: ")
        space_title = input("space title: ")
        space_date = input("space date: ")
        t1 = threading.Thread(target=loading_text)
        t1.start()
        download(m3u8_id, space_id, twitter_name, space_title, space_date, server)
        status = False
        exit()
    except Exception as e:
        print(f"\rError encountered...\n{e}")
        while True:
            input("Exit...")
            exit()
