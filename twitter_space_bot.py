import time
import tweepy
import xhr_grabber
import requests
import twspace
import threading
import re
import subprocess
import const
from datetime import datetime

SLEEP_TIME = const.SLEEP_TIME
api_key = const.api_key
api_key_secret = const.api_key_secret
bearer_token = const.bearer_token
access_token = const.access_token
access_token_secret = const.access_token_secret
WEBHOOK_URL = const.WEBHOOK_URL
DOWNLOAD = const.DOWNLOAD
RYU_DOWNLOAD = const.RYU_DOWNLOAD

# Authorize and setup twitter client
auth = tweepy.OAuthHandler(api_key, api_key_secret)
auth.set_access_token(access_token, access_token_secret)
api = tweepy.API(auth)
twitter_client = tweepy.Client(bearer_token, consumer_key=api_key, consumer_secret=api_key_secret,
                               access_token=access_token, access_token_secret=access_token_secret)

# List of twitter creators to monitor
twitter_ids = const.twitter_ids

space_fields = ['id', 'state', 'title', 'started_at']
user_fields = ['profile_image_url']
expansions = ['creator_id', 'host_ids']

twitter_id_list = []
for twitter_user in twitter_ids:
    twitter_id_list.append(str(*twitter_user.values()))

user_ids = ",".join(twitter_id_list)

notified_spaces = []


def get_m3u8_id(url):
    return re.search("(.*\/Transcoding\/v1\/hls\/(.*)(\/non_transcode.*))", url).group(2)


def get_spaces():
    try:
        # for some darn reason space_fields do not work
        req = twitter_client.get_spaces(expansions=expansions, user_ids=twitter_id_list, space_fields=space_fields, user_fields=user_fields)
    except Exception as e:
        print(f"[error] {e}")
        return []
    # response example with two difference spaces
    # Response(data=[<Space id=1vOGwyQpQAVxB state=live>, <Space id=1ypKdEePLXLGW state=live>], includes={'users': [<User id=838403636015185920 name=Misaネキ username=Misamisatotomi>, <User id=1181889913517572096 name=アステル・レダ🎭 / オリジナルソングMV公開中!! username=astelleda>]}, errors=[], meta={'result_count': 2})
    spaces = []
    result_count = req[3]["result_count"]
    if result_count != 0:
        datas = req[0]
        users = req[1]["users"]
        for data, user in zip(datas, users):
            spaces.append([data, user])
    return spaces


def download(notified_space):
    if DOWNLOAD is not None or False:
        notified_space_id = notified_space[0]["id"]
        notified_space_creator = notified_space[1]
        notified_space_started_at = notified_space[0].started_at.strftime("%Y%m%d")
        notified_space_title = notified_space[0].title
        notified_space_m3u8_id = get_m3u8_id(notified_space[2])
        print(f'[info] Starting download since {notified_space_creator} is now offline at {notified_space_id}')
        threading.Thread(target=twspace.download,
                         args=[notified_space_m3u8_id, notified_space_id, notified_space_creator,
                               notified_space_title, notified_space_started_at]).start()
    elif RYU_DOWNLOAD is not None or False:
        notified_space_id = notified_space[0]["id"]
        notified_space_m3u8_id = notified_space[2]
        command_list = ["twspace_dl.exe", "-i", f"https://twitter.com/i/spaces/{notified_space_id}"]
        # Use default command if download output is not specified
        if RYU_DOWNLOAD:
            command_list += ['-f', notified_space_m3u8_id]
        else:
            command_list += ['-f', notified_space_m3u8_id, '-o', RYU_DOWNLOAD]
        try:
            subprocess.run(command_list)
        except Exception as e:
            print("[error] Aborting download please download manually")
            print(f"[error] {e}")


def check_status(notified_spaces, space_list):
    if len(notified_spaces) != 0:
        for notified_space in notified_spaces:
            counter = 0
            if len(space_list) == 0:
                try:
                    download(notified_space)
                except Exception as e:
                    print(f"[error] Error, aborting download, please download manually")
                    print(f"[error] {e}")
                notified_spaces.remove(notified_space)

            for space in space_list:
                if len(space_list) == 0 or counter == len(space_list) and notified_space[0]["id"] != space[0]["id"]:
                    try:
                        download(notified_space)
                    except Exception as e:
                        print(f"[error] Error, aborting download, please download manually")
                        print(f"[error] {e}")
                    notified_spaces.remove(notified_space)
                counter += 1


if __name__ == "__main__":
    notified_spaces = []
    while True:
        try:
            space_list = get_spaces()
            check_status(notified_spaces, space_list)

            # Get and send out space url and m3u8 to discord webhook
            for space in space_list:
                if len(space_list) != 0:
                    space_id = space[0]["id"]
                    if not any(space_id == notified_space[0]["id"] for notified_space in notified_spaces):
                        status = space[0]["state"]
                        creator_profile_image = space[1].profile_image_url
                        space_creator = space[1]
                        if space[0] is not None:
                            space_started_at = space[0].started_at.strftime("%Y%m%d")
                        else:
                            space_started_at = datetime.utcnow().strftime("%Y%m%d")
                        space_title = space[0].title
                        space_url = f"https://twitter.com/i/spaces/{space_id}"

                        # Get and send the m3u8 url
                        m3u8_url = xhr_grabber.get_m3u8(space_url)
                        if m3u8_url is not None:
                            print(f"[info] {space_creator} is now {status} at {space_url} \n[info] M3U8: {m3u8_url}")
                            # message = {'content': f"`{space_creator}` is now `{status}` at {space_url} ```{m3u8_url}```"}
                            message = {"embeds": [{
                                "author": {
                                    "name": f"{space_creator}",
                                    "icon_url": creator_profile_image
                                },
                                "fields": [
                                    {
                                        "name": "Live Space",
                                        "value": f"{space_creator} is now {status} at [{space_url}]({space_url}) ```{m3u8_url}```"
                                    }
                                ],
                                "thumbnail": {
                                    "url": creator_profile_image.replace("normal", "200x200")
                                }
                            }]
                            }
                            if WEBHOOK_URL is not None:
                                requests.post(WEBHOOK_URL, json=message)
                            m3u8_id = m3u8_url
                            notified_space = space
                            notified_space.append(m3u8_id)
                            notified_spaces.append(notified_space)
            print(f"[info] Sleeping for {SLEEP_TIME} secs...")
            time.sleep(SLEEP_TIME)
        except Exception as e:
            print(f"[error] {e}")