import os
import urllib.request
import re
import subprocess
import const
import discord
import shutil


# Function takes in the file name and check if it contains illegal characters
# If it contains an illegal character then remove it and return the new file name without the illegal character
def checkFileName(fileName):
    invalidName = re.compile(r"[\\*?<>:\"/\|]")
    newFileName = fileName
    if re.search(invalidName, fileName) is not None:
        newFileName = re.sub(invalidName, "_", fileName)
        # print("\nInvalid File Name Detected\nNew File Name: " + newFileName)
    # If file name has multiple lines then join them together(because stripping newline doesn't work)
    if "\n" in fileName:
        title_array = fileName.splitlines()
        newFileName = " ".join(title_array)
    return newFileName


def send_file(file_path, space_id, twitter_name, space_title, space_date):
    if os.path.isfile(file_path):
        webhook = discord.Webhook.from_url(const.WEBHOOK_DOWNLOAD_URL, adapter=discord.RequestsWebhookAdapter())
        space_file = discord.File(file_path)
        content = f"The twitter space for {twitter_name} was downloaded\n`[{space_date}]{twitter_name} - {space_title}({space_id})`"
        try:
            webhook.send(content=content, file=space_file)
        except discord.HTTPException as e:
            print(f"[error] {e}")
    else:
        print("[error] Could not find space file to send")


def download(m3u8_id, space_id, twitter_name, space_title, space_date):
    DOWNLOAD_PATH = const.DOWNLOAD
    if DOWNLOAD_PATH == "True":
        DOWNLOAD_PATH = os.getcwd()
    elif not os.path.exists(DOWNLOAD_PATH):
        os.makedirs(DOWNLOAD_PATH)

    base_url = 'https://prod-fastly-us-east-1.video.pscp.tv'
    base_addon = '/Transcoding/v1/hls/'

    file_name = checkFileName(space_title)

    end_masterurl = "/non_transcode/us-east-1/periscope-replay-direct-prod-us-east-1-public/audio-space/master_playlist.m3u8"
    end_chunkurl = '/non_transcode/ap-northeast-1/periscope-replay-direct-prod-ap-northeast-1-public/audio-space/chunk'
    master_url = base_url+base_addon+m3u8_id+end_masterurl
    t = urllib.request.urlopen(master_url).read().decode('utf-8')
    master_playlist = re.findall(".*m3u8$", t, re.MULTILINE)
    for i in master_playlist:
        master_playlist = i

    chunk_m3u8 = base_url+master_playlist

    t = urllib.request.urlopen(chunk_m3u8).read().decode('utf-8')
    t = t.replace('chunk', base_url+base_addon+m3u8_id+end_chunkurl)

    filename = f'{space_id}.m3u8'
    output = f'{DOWNLOAD_PATH}\\{space_date} - {twitter_name} - {file_name} ({space_id}).aac'
    command = f'ffmpeg -n -hide_banner -loglevel error -protocol_whitelist file,https,tls,tcp -i {filename} -metadata date=2021 -metadata comment={m3u8_id} -metadata artist={twitter_name} -c copy "{output}"'

    with open(filename, 'x') as f:
        f.write(t)
        os.system(command)

    # Only run kid3-cli to set metadata if kid3-cli exist or in path
    if shutil.which("kid3-cli") is not None:
        #Add metadata using kid3 and metadata
        #Note metadata won't be shown when using vlc
        kids3_list = ['kid3-cli', '-c', 'set date "2021"', '-c', f'set artist "{twitter_name}"', '-c', f'set comment "{m3u8_id}"', output]
        subprocess.run(kids3_list)

    os.remove(filename)

    send_file(output, space_id, twitter_name, space_title, space_date)

