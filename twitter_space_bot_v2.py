import sys
import time
from CallbackRetry import CallbackRetry
import urllib3
from requests.adapters import HTTPAdapter, MaxRetryError
from urllib3 import Retry
import requests
import twspace
import threading
import re
import const
from datetime import datetime
from log import create_logger
import logging
from TwitterSpace import TwitterSpace


# TODO: Worked on twspace, test and ensure it works and make sure main function changes from object to variable arguments
# Major Changes: Setted TwitterSpaces which is a dictionary of TwitterSpace objects e.g.{'user_id': TwitterSpace(handle_id='sam', handle_name='sam', handle_image=None, space_id=None, space_title=None, space_started_at='20230409', space_url=None, m3u8_url=None, space_notified=False, space_downloaded=False, space_duration=0, periscope_server=None, deployment_server=None, rest_id=None, media_key=None)}

SLEEP_TIME = const.SLEEP_TIME
# api_key = const.api_key
# api_key_secret = const.api_key_secret
# bearer_token = const.bearer_token
# access_token = const.access_token
# access_token_secret = const.access_token_secret
WEBHOOK_URL = const.WEBHOOK_URL
DOWNLOAD = const.DOWNLOAD

# Authorize and setup twitter client
BEARER_TOKEN = "Bearer AAAAAAAAAAAAAAAAAAAAANRILgAAAAAAnNwIzUejRCOuH5E6I8xnZz4puTs=1Zv7ttfk8LF81IUq16cHjhLTvJu4FA33AGWWjCpTnA"
guest_token = ""
rate_limit_remaining = 500

# List of twitter creators to monitor
twitter_ids = const.twitter_ids
TwitterSpaces = {}

space_fields = ['id', 'state', 'title', 'started_at', 'ended_at']
user_fields = ['profile_image_url']
expansions = ['creator_id', 'host_ids', 'invited_user_ids']

#################################
"""
API FUNCTIONS
"""


def set_logger(logger=None):
    if logger is None:
        logger = logging.getLogger(__name__)
        if len(logger.handlers) != 0:
            return logger
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        formatter = logging.Formatter('%(asctime)s [%(filename)s:%(lineno)d] %(levelname)s | %(message)s',
                                      datefmt='%Y-%m-%d %H:%M:%S')
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)
    return logger

def callback_func():
    print("Retrying...")
    renew_guest_token()

def create_session():
    session = requests.Session()
    retry = CallbackRetry(total=5, backoff_factor=2, status_forcelist=[400, 401, 403, 404, 429, 443, 500, 502, 503, 504], callback=callback_func)
    session.mount("https://", HTTPAdapter(max_retries=retry))
    return session


def before_backoff(retry_object, **kwargs):
    print("Renewing token before retry")
    renew_guest_token()


def fix_up_user_array(logger=None):
    global twitter_ids
    logger = set_logger(logger)

    handle_name = None
    for user_dict in const.twitter_ids:
        try:
            handle_name, handle_id = user_dict.popitem()
            twitter_ids.append({'name': handle_name, 'id': str(handle_id)})
            raise Exception
        except Exception as e:
            logger.error(f"Issue with providing user IDs {handle_name if handle_name is not None else ''}: Error {e}")
            sys.exit()


def renew_guest_token(logger=None, session=None):
    global guest_token
    global rate_limit_remaining
    logger = set_logger(logger)

    guest_token_url = "https://api.twitter.com/1.1/guest/activate.json"
    while True:
        try:
            guest_token_response = requests.post(url=guest_token_url, headers={"Authorization": BEARER_TOKEN})
            logger.debug(f"Guest Token Response: {guest_token_response}")
            if guest_token_response.status_code == 200:
                logger.info(f"Renewed Guest Token: {guest_token}")
                guest_token = guest_token_response.json()["guest_token"]
                rate_limit_remaining = 500
                return guest_token
            else:
                logger.debug(f"STATUS CODE {guest_token_response.status_code}: {guest_token_response.reason}")
        except requests.RequestException as rException:
            logger.error(rException)
            logger.info("Error renewing guest token, retrying in 20 secs...")
            time.sleep(20)
            continue


# Gets the first twitter space on the timeline/user profile
# Returns the space id
def get_space_tweet_id(handle_id, handle_name, logger=None, session=None):
    global rate_limit_remaining
    # logger = set_logger(logger)
    if rate_limit_remaining == 0:
        renew_guest_token(logger=logger, session=session)

    space_id_pattern = r'"expanded_url":"https://twitter\.com/i/spaces/(.*?)"'

    # See UserTweets.json for example json response
    space_id_url = "https://api.twitter.com/graphql/rCpYpqplOq3UJ2p6Oxy3tw/UserTweets"
    headers = {"Authorization": BEARER_TOKEN, "x-guest-token": guest_token}

    params = {
        "variables": f'{{"userId":"{handle_id}",'
                     '"count":10,"includePromotedContent":true,'
                     '"withQuickPromoteEligibilityTweetFields":true,'
                     '"withSuperFollowsUserFields":true,'
                     '"withDownvotePerspective":false,'
                     '"withReactionsMetadata":false,'
                     '"withReactionsPerspective":false,'
                     '"withSuperFollowsTweetFields":false,'
                     '"withVoice":false,"withV2Timeline":false}',
        "features": '{"responsive_web_twitter_blue_verified_badge_is_enabled": true,'
                     '"responsive_web_graphql_exclude_directive_enabled": false,'
                     '"verified_phone_label_enabled": false,'
                     '"responsive_web_graphql_timeline_navigation_enabled": true,'
                     '"responsive_web_graphql_skip_user_profile_image_extensions_enabled": false,'
                     '"tweetypie_unmention_optimization_enabled": true,'
                     '"vibe_api_enabled": true,'
                     '"responsive_web_edit_tweet_api_enabled": true,'
                     '"graphql_is_translatable_rweb_tweet_is_translatable_enabled": true,'
                     '"view_counts_everywhere_api_enabled": true,'
                     '"longform_notetweets_consumption_enabled": true,'
                     '"freedom_of_speech_not_reach_appeal_label_enabled": false,'
                     '"standardized_nudges_misinfo": true,'
                     '"tweet_with_visibility_results_prefer_gql_limited_actions_policy_enabled": false,'
                     '"interactive_text_enabled": true,'
                     '"responsive_web_text_conversations_enabled": false,'
                     '"responsive_web_enhance_cards_enabled": false}'
    }
    rest_id_response = session.get(url=space_id_url, headers=headers, params=params)

    # Error check
    if rest_id_response.status_code != 200:
        # if 'error' in rest_id_response.json():
        #     if rest_id_response.json().get('errors').get(0).get('code') == 239:
        #         logger.info("Bad guest token, renewing...")
        #         renew_guest_token(logger=logger, session=session)
        logger.error(f"Error {rest_id_response.status_code}: {rest_id_response.text}")
        logger.error(f"Issue getting space id for {handle_name}")
        renew_guest_token(logger=logger, session=session)
    elif 'data' not in rest_id_response.json():
        logger.info(rest_id_response)

    rate_limit_remaining -= 1
    # space_id = space_id_response.json()['data']['user']['result']['timeline_v2']['timeline']['instructions'][0]['entries'][0]['result']['legacy']['extended_entities']['media']['media_key']
    # print(rest_id_response.text)
    rest_id = None
    try:
        rest_id = re.search(string=rest_id_response.text, pattern=space_id_pattern).group(1)
        logger.debug(f"Space ID for {handle_name}({handle_id}): {rest_id}")
    except AttributeError as attr_error:
        # logger.debug(attr_error)
        pass
    return rest_id


# Gets detailed information/status of the twitter space
# Returns a media key which is used to get information about the video stream(m3u8 url)
def get_space_details(handle_name, rest_id, logger=None, session=None):
    global rate_limit_remaining
    logger = set_logger(logger)

    if rate_limit_remaining == 0:
        renew_guest_token(logger=logger, session=session)

    # See AudioSpaceById for example json response
    space_id_url = "https://api.twitter.com/graphql/yJf1x-eRmSjgEkJcAHh_lA/AudioSpaceById"
    headers = {"Authorization": BEARER_TOKEN, "x-guest-token": guest_token}
    params = {
        "variables": f'{{"id":"{rest_id}",'
                     '"isMetatagsQuery":false,'
                     '"withSuperFollowsUserFields":true,'
                     '"withDownvotePerspective":false,'
                     '"withReactionsMetadata":false,'
                     '"withReactionsPerspective":false,'
                     '"withSuperFollowsTweetFields":true,'
                     '"withReplays":true}',
        "features": '{"spaces_2022_h2_clipping":true,'
                     '"spaces_2022_h2_spaces_communities":true,'
                     '"responsive_web_twitter_blue_verified_badge_is_enabled":true,'
                     '"responsive_web_graphql_exclude_directive_enabled":false,'
                     '"verified_phone_label_enabled":false,'
                     '"responsive_web_graphql_skip_user_profile_image_extensions_enabled":false,'
                     '"tweetypie_unmention_optimization_enabled":true,'
                     '"vibe_api_enabled":true,'
                     '"responsive_web_edit_tweet_api_enabled":true,'
                     '"graphql_is_translatable_rweb_tweet_is_translatable_enabled":true,'
                     '"view_counts_everywhere_api_enabled":true,'
                     '"longform_notetweets_consumption_enabled":true,'
                     '"freedom_of_speech_not_reach_appeal_label_enabled":false,'
                     '"standardized_nudges_misinfo":true,'
                     '"tweet_with_visibility_results_prefer_gql_limited_actions_policy_enabled":false,'
                     '"responsive_web_graphql_timeline_navigation_enabled":true,'
                     '"interactive_text_enabled":true,'
                     '"responsive_web_text_conversations_enabled":false,'
                     '"responsive_web_enhance_cards_enabled":false}'
    }
    space_id_response = session.get(url=space_id_url, headers=headers, params=params)

    # Error check
    space_id_json = space_id_response.json()
    logger.debug(space_id_json)

    if 'data' not in space_id_json or space_id_response.status_code != 200:
        if 'error' in space_id_json:
            if space_id_json['errors'][0]['code'] == 239:
                logger.info("Bad guest token, renewing...")
                renew_guest_token(logger=logger, session=session)
            logger.error(f"Error {space_id_response.status_code}: {space_id_json}")
            logger.error(f"Issue getting media key for {handle_name}")
            return None
        else:
            # {'data': {'audioSpace': {}}}
            logger.debug("Empty object received...")
            return None
    elif space_id_json.get('data').get('audioSpace') == {}:
        # {'data': {'audioSpace': {}}}
        return None
    rate_limit_remaining -= 1

    return space_id_response


def get_media_key(space_detail, logger=None):
    # logger = set_logger(logger)
    media_key = None
    # media_key_pattern = r'"media_key":"(.*?)"'
    # space_id = space_id_response.json()['data']['user']['result']['timeline_v2']['timeline']['instructions'][0]['entries'][0]['result']['legacy']['extended_entities']['media']['media_key']
    try:
        # media_key = re.search(string=space_detail.text, pattern=media_key_pattern).group(1)
        media_key = space_detail['media_key']
        logger.debug(f"Media Key: {media_key}")
    except (AttributeError, KeyError):
        logger.error("Issue finding media key")
        logger.debug(space_detail)
    return media_key


# Gets detailed information about the video/media stream
# Returns m3u8 url
def get_space_source(media_key, logger=None, session=None):
    logger = set_logger(logger)
    location_url = None
    # See live_video_stream for example json response
    space_source_url = f"https://api.twitter.com/1.1/live_video_stream/status/{media_key}"

    try:
        space_source_response = session.get(url=space_source_url)
    except (requests.exceptions.RequestException, urllib3.exceptions.MaxRetryError, requests.exceptions.RetryError) as e:
        logger.error(e)

    if space_source_response.status_code != 200:
        logger.error(f"Error {space_source_response.status_code}")
        return location_url

    space_source = space_source_response.json()
    location_url = space_source["source"]["location"].replace("dynamic", "master").replace("?type=live", "")
    logger.debug(space_source)
    return location_url


def create_users():
    for user in twitter_ids:
        user_name, user_id = user.popitem()
        TwitterSpaces[user_id] = TwitterSpace(handle_id=str(user_id), handle_name=user_name)


def get_spaces(logger=None, session=None):
    for user in TwitterSpaces.values():
        try:
            rest_id = get_space_tweet_id(user.handle_id, user.handle_name, logger=logger, session=session)
            if rest_id is None:
                logger.info(f"{user.handle_name} is currently offline...")
                continue
            user.rest_id = rest_id
            space_details = get_space_details(user.handle_name, rest_id, logger=logger, session=session)

            if space_details is None:
                continue
                logger.info(f"{user.handle_name} is currently offline...")
            else:
                space_details = space_details.json()['data']['audioSpace']['metadata']
                if user.space_state == space_details['state'] or user.space_state is None and space_details['state'] == 'Ended':
                    continue

            media_key = get_media_key(space_details, logger=logger)
            user.media_key = media_key
            user.set_space_details(space_details)
        except Exception:
            logger.error(f"Issue getting latest space id from {user.handle_name}", exc_info=True)
            continue


def download(ended_spaces, logger=None):
    if DOWNLOAD is not None or False:
        for ended_space in ended_spaces:
            if int(ended_space.space_duration) == 0:
                duration = datetime.timestamp(datetime.now()) - ended_space.space_started_at/1000.0
                ended_space.space_duration = duration
            # ended_space.m3u8_url = get_space_source(media_key=ended_space.media_key, logger=logger)
            # print(" " * 70, end='\n')
            logger.info(f"{ended_space.handle_name} is now offline at {ended_space.rest_id}{' ' * 20}")
            try:
                threading.Thread(target=twspace.download,
                                 args=[ended_space.get_m3u8_id, ended_space.rest_id, ended_space.handle_name,
                                       ended_space.space_title, ended_space.get_server,
                                       ended_space.space_duration, ended_space.get_strftime, logger]).start()
                ended_space.space_downloaded = True
            except Exception as thread_exception:
                logger.error(thread_exception, exc_info=True)
                ended_space.space_downloaded = False


# def check_status(space_list, notified_spaces):
#     # Check if a space went offline to download
#     offline_spaces = []
#     for notified_space in notified_spaces:
#         if not any(space[0]["id"] == notified_space[0]["id"] for space in space_list):
#             try:
#                 logger.debug(notified_space)
#                 logger.debug(space_list)
#                 offline_spaces.append(notified_space)
#                 download(notified_space)
#             except Exception as e:
#                 logger.error(e, exc_info=True)
#
#     # Remove offline spaces from notified spaces
#     for offline_space in offline_spaces:
#         notified_spaces.remove(offline_space)


def loading_text():
    loading_string = "Waiting for live twitter spaces "
    animation = ["     ", ".    ", "..   ", "...  ", ".... ", "....."]
    idx = 0
    while True:
        print(f"[INFO] {datetime.now().replace(microsecond=0)} | " + loading_string + animation[idx % len(animation)],
              end="\r")
        time.sleep(0.3)
        idx += 1
        if idx == 6:
            idx = 0


if __name__ == "__main__":
    logger = create_logger("logfile.log")
    logger.info("Starting program")
    threading.Thread(target=loading_text).start()
    session = create_session()
    # loading_string = "[INFO] Waiting for live twitter spaces"
    create_users()

    while True:
        try:
            get_spaces(logger=logger, session=session)
            space_list = [space for space in TwitterSpaces.values() if space.space_state == "Running" and not space.space_notified]
            to_download = [space for space in TwitterSpaces.values() if space.space_state == "Ended" and not space.space_downloaded and space.space_was_running]

            if space_list is None:
                continue

            # Download spaces that have ended and have yet to be downloaded
            if to_download is not None:
                logger.debug(to_download)
                download(to_download, logger=logger)


            # Get and send out space url and m3u8 to discord webhook
            for space in space_list:
                logger.debug(f"Space Object: {str(space)}")
                # logger.debug(f"Space Details: {str(space[0]['data'])}")
                # logger.debug(f"User Details: {str(space[1]['data'])}")
                space_id = space.rest_id
                status = 'live' if space.space_state == 'Running' else space.space_state
                creator_profile_image = space.handle_image
                space_creator = space.handle_name
                space_started_at = space.get_strftime()
                space_title = space.space_title

                space_url = f"https://twitter.com/i/spaces/{space_id}"

                # Get and send the m3u8 url
                m3u8_url = get_space_source(media_key=space.media_key, session=session, logger=logger)
                space.m3u8_url = m3u8_url
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
                        session.post(WEBHOOK_URL, json=message)
                    space.space_notified = True
            time.sleep(SLEEP_TIME)
        except SystemExit:
            sys.exit()
        except OSError:
            sys.exit()
        except KeyboardInterrupt:
            sys.exit()
        except Exception as e:
            logger.error(e, exc_info=True)
