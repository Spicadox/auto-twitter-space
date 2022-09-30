import sys
import time
import tweepy
import urllib3
import xhr_grabber
import requests
import twspace
import threading
import re
import const
from datetime import datetime
from log import create_logger


SLEEP_TIME = const.SLEEP_TIME
api_key = const.api_key
api_key_secret = const.api_key_secret
bearer_token = const.bearer_token
access_token = const.access_token
access_token_secret = const.access_token_secret
WEBHOOK_URL = const.WEBHOOK_URL
DOWNLOAD = const.DOWNLOAD


# Authorize and setup twitter client
auth = tweepy.OAuthHandler(api_key, api_key_secret)
auth.set_access_token(access_token, access_token_secret)
api = tweepy.API(auth)
twitter_client = tweepy.Client(bearer_token, consumer_key=api_key, consumer_secret=api_key_secret,
                               access_token=access_token, access_token_secret=access_token_secret)

# List of twitter creators to monitor
twitter_ids = const.twitter_ids

space_fields = ['id', 'state', 'title', 'started_at', 'ended_at']
user_fields = ['profile_image_url']
expansions = ['creator_id', 'host_ids', 'invited_user_ids']


def get_user_ids():
    user_ids = []
    split_twitter_id_list = []
    if len(twitter_ids) // 100 != 0:
        for split in range(len(twitter_ids) // 100):
            split_twitter_id_list += [twitter_ids[split * 100:(split + 1) * 100]]
        if len(twitter_ids) % 100 != 0:
            split_twitter_id_list += [twitter_ids[(len(twitter_ids) // 100) * 100:]]
    else:
        split_twitter_id_list = [twitter_ids]

    for twitter_user_list in split_twitter_id_list:
        temp_id = []
        for twitter_user in twitter_user_list:
            temp_id.append(str(*twitter_user.values()))
        user_ids.append(temp_id)
    return user_ids


def get_m3u8_id(url):
    return re.search("(.*\/Transcoding\/v1\/hls\/(.*)(\/non_transcode.*))", url).group(2)


# return a tuple of (deployment server, periscope server) where
# deployment server can be either prod-fastly or canary-video while a periscope server can be ap-northeast-1.video or us-east-1
def get_server(url):
    reg_result = re.search("(https:\/\/)((?:[^-]*-){2})(.*)(\.pscp.*)", url)
    # regex will return something like 'prod-fastly-' so remove the last dash
    deployment_server = reg_result.group(2)[:-1]
    periscope_server = reg_result.group(3)
    server = (deployment_server, periscope_server)
    return server


def get_spaces(user_ids):
    spaces = []
    user_ids_copy = user_ids.copy()
    max_retry = 10
    retry = 1
    while len(user_ids_copy) != 0:
        for split_user_id in user_ids_copy:
            try:
                req = twitter_client.get_spaces(expansions=expansions, user_ids=split_user_id, space_fields=space_fields, user_fields=user_fields)
                if req[0] is not None or len(req[1]) != 0:
                    logger.debug(req)
                # Used list comprehension to create and set the new list instead of mutating and removing id
                user_ids_copy = [split_id for split_id in user_ids_copy if not split_user_id]
            except requests.exceptions.ConnectionError as cError:
                logger.debug(cError)
                # logger.debug(requests.status_codes._codes[cError.response.status_code][0])
                if retry != max_retry+1:
                    logger.warning(f"Connection Error: Retry ({retry}/{max_retry})")
                    retry += 1
                time.sleep(10)
                break
            except (tweepy.errors.TwitterServerError, tweepy.errors.TooManyRequests) as tweepyError:
                # Catches 503 Service Unavailable
                logger.debug(tweepyError)
                logger.warning(f"{tweepyError.response.status_code} {tweepyError.response.reason}: Retry ({retry}/{max_retry})")
                if retry != max_retry+1:
                    logger.debug(f"Spaces to retry: {str(split_user_id)}")
                    retry += 1
                time.sleep(10)
                break
            except (requests.exceptions.RequestException, urllib3.exceptions.MaxRetryError) as e:
                logger.debug(e, exc_info=True)
                if retry != max_retry+1:
                    logger.debug(e, exc_info=True)
                    logger.warning(f"Polling spaces error retry {retry}/{max_retry}")
                    retry += 1
                time.sleep(10)
                break

            # response example with two difference spaces
            # Response(data=[<Space id=1vOGwyQpQAVxB state=live>, <Space id=1ypKdEePLXLGW state=live>], includes={'users': [<User id=838403636015185920 name=Misaネキ username=Misamisatotomi>, <User id=1181889913517572096 name=アステル・レダ🎭 / オリジナルソングMV公開中!! username=astelleda>]}, errors=[], meta={'result_count': 2})
            result_count = req[3]["result_count"]
            if result_count != 0:
                datas = req[0]
                users = req[1]["users"]
                for data, user in zip(datas, users):
                    spaces.append([data, user])
            time.sleep(5)
        if retry == max_retry:
            logger.error(f"Retry Exceeded ({retry}/{max_retry})")
            logger.debug(f"Giving up on: {user_ids_copy}")
            # If there is a live space then return that otherwise return None to avoid prematurely downloading live space
            if len(spaces) != 0:
                break
            else:
                return None
    return spaces


def download(notified_space):
    if DOWNLOAD is not None or False:
        notified_space_id = notified_space[0]["id"]
        notified_space_creator = notified_space[1]
        if notified_space[0] is not None:
            notified_space_started_at = notified_space[0].started_at
            duration = datetime.timestamp(datetime.now()) - datetime.timestamp(notified_space_started_at)
            notified_space_started_at = notified_space_started_at.strftime("%Y%m%d")
        else:
            notified_space_started_at = datetime.utcnow().strftime("%Y%m%d")
            duration = 0
        notified_space_title = notified_space[0].title
        # Use default space title if it's not supplied
        if notified_space_title is None:
            notified_space_title = f"{notified_space_creator} space"
        notified_space_m3u8_id = get_m3u8_id(notified_space[2])
        notified_space_periscope_server = get_server(notified_space[2])
        print(" " * 70, end='\n')
        logger.info(f"{notified_space_creator} is now offline at {notified_space_id}{' '*20}")
        threading.Thread(target=twspace.download,
                         args=[notified_space_m3u8_id, notified_space_id, notified_space_creator, notified_space_title,
                               notified_space_started_at, notified_space_periscope_server, duration]).start()


def check_status(space_list, notified_spaces):
    # Check if a space went offline to download
    offline_spaces = []
    for notified_space in notified_spaces:
        if not any(space[0]["id"] == notified_space[0]["id"] for space in space_list):
            try:
                logger.debug(notified_space)
                logger.debug(space_list)
                offline_spaces.append(notified_space)
                download(notified_space)
            except Exception as e:
                logger.error(e, exc_info=True)

    # Remove offline spaces from notified spaces
    for offline_space in offline_spaces:
        notified_spaces.remove(offline_space)


def loading_text():
    loading_string = "Waiting for live twitter spaces "
    animation = ["     ", ".    ", "..   ", "...  ", ".... ", "....."]
    idx = 0
    while True:
        print(f"[INFO] {datetime.now().replace(microsecond=0)} | " + loading_string + animation[idx % len(animation)], end="\r")
        time.sleep(0.3)
        idx += 1
        if idx == 6:
            idx = 0


if __name__ == "__main__":
    logger = create_logger("logfile.log")
    notified_spaces = []
    logger.info("Starting program")
    threading.Thread(target=loading_text).start()
    # loading_string = "[INFO] Waiting for live twitter spaces"
    user_ids = get_user_ids()
    while True:
        try:
            space_list = get_spaces(user_ids)
            # If there was an error then continue the loop
            if space_list is None:
                continue
            check_status(space_list, notified_spaces)

            # Get and send out space url and m3u8 to discord webhook
            for space in space_list:
                logger.debug(f"Space Object: {str(space)}")
                logger.debug(f"Space Details: {str(space[0]['data'])}")
                logger.debug(f"User Details: {str(space[1]['data'])}")
                if len(space_list) != 0:
                    # Ignore if the space is scheduled to be live
                    if space[0]['state'] == 'scheduled':
                        continue
                    space_id = space[0]["id"]
                    if not any(space_id == notified_space[0]["id"] for notified_space in notified_spaces):
                        status = space[0]["state"]
                        creator_profile_image = space[1].profile_image_url
                        space_creator = space[1]
                        space_started_at = space[0].started_at.strftime("%Y%m%d")
                        space_title = space[0].title
                        # If no space title has been set then go with the default
                        if space_title is None:
                            space_title = "Twitter Space"
                        space_url = f"https://twitter.com/i/spaces/{space_id}"

                        # Get and send the m3u8 url
                        m3u8_url = xhr_grabber.get_m3u8(space_url)
                        if m3u8_url is not None:
                            # Todo maybe consider changing space_creator to `space_creator` to avoid underscore error
                            logger.info(f"{space_creator} is now {status} at {space_url}")
                            logger.info(f"M3U8: {m3u8_url}")
                            message = {"embeds": [{
                                "color": 1942002,
                                "author": {
                                    "name": f"{space_creator}",
                                    "icon_url": creator_profile_image
                                },
                                "fields": [
                                    {
                                        "name": space_title,
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
            time.sleep(SLEEP_TIME)
        except SystemExit:
            sys.exit()
        except OSError:
            sys.exit()
        except KeyboardInterrupt:
            sys.exit()
        except Exception as e:
            logger.error(e, exc_info=True)

