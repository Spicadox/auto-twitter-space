import json
import sys
import time
import urllib3
import requests
import twspace
import threading
import re
import const
from datetime import datetime
from log import create_logger
import logging
from TwitterSpace import TwitterSpace


# TODO: Look into how to handle retweeted spaces and scheduled spaces -> avoid space being downloaded multiple times(create a download list to check spaces being downloaded?)
# TODO: Look into how to better handle and show twitter participant level(speaker, listener, etc)

# Major Changes: Setted TwitterSpaces which is a dictionary of TwitterSpace objects e.g.{'user_id': TwitterSpace(handle_id='sam', handle_name='sam', handle_image=None, space_id=None, space_title=None, space_started_at='20230409', space_url=None, m3u8_url=None, space_notified=False, space_downloaded=False, space_duration=0, periscope_server=None, deployment_server=None, rest_id=None, media_key=None)}
SLEEP_TIME = const.SLEEP_TIME
ALL_SPACE_TIMELINE = const.ALL_SPACE_TIMELINE

WEBHOOK_URL = const.WEBHOOK_URL
DOWNLOAD = const.DOWNLOAD

BEARER_TOKEN = const.BEARER_TOKEN
AUTH_TOKEN = const.AUTH_TOKEN
CSRF_TOKEN = const.CT0

# List of twitter creators to monitor
twitter_ids = const.twitter_ids
TwitterSpaces = {}

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


def handle_rate_limit(handle_name, header_json, logger=None):
    logger = set_logger(logger)
    logger.debug(f"[{handle_name}] Headers: {header_json}")
    x_rate_limit_remaining = int(header_json.get("x-rate-limit-remaining", 0))
    x_rate_limit_reset = int(header_json.get("x-rate-limit-reset"))

    if x_rate_limit_remaining == 0:
        rate_limit_duration = (datetime.fromtimestamp(x_rate_limit_reset) - datetime.now()).total_seconds()
        logger.warning(
            f"[{handle_name}] Rate-limited until {datetime.fromtimestamp(x_rate_limit_reset)}, sleeping for {int(rate_limit_duration)} seconds...")
        time.sleep(rate_limit_duration or SLEEP_TIME)


# Get the creator of the space and title of the current user(admin, speaker or None)
def get_space_participant(user, space_details):
    # Check if space is created by the current space user and not a retweeted space on timeline,etc
    space_details_json = space_details.json()
    space_creator_id = space_details_json['data']['audioSpace']['metadata']['creator_results']['result']['rest_id']
    space_creator_name = space_details_json['data']['audioSpace']['metadata']['creator_results']['result']['legacy']['screen_name']

    if user.handle_id in json.dumps(space_details_json['data']['audioSpace']['participants']['admins']):
        participant_title = 'admin'
    elif user.handle_id in json.dumps(space_details_json['data']['audioSpace']['participants']['speakers']):
        participant_title = 'speaker'
    elif user.handle_id in json.dumps(space_details_json['data']['audioSpace']['participants']['listeners']):
        participant_title = 'listener'
    else:
        participant_title = 'unknown'

    return space_creator_id, space_creator_name, participant_title


# Gets the first twitter space on the timeline/user profile
# Returns the space id
def get_space_tweet_id(handle_id, handle_name, logger=None):
    logger = set_logger(logger)

    space_id_pattern = r'"expanded_url":"https://twitter\.com/i/spaces/(.*?)"'

    # See UserTweets.json for example json response
    space_id_url = "https://twitter.com/i/api/graphql/rIIwMe1ObkGh_ByBtTCtRQ/UserTweets"
    headers = {"Authorization": BEARER_TOKEN, "X-Csrf-Token": CSRF_TOKEN}
    cookies = {"auth_token": AUTH_TOKEN, "ct0": CSRF_TOKEN}

    params = {
        "variables": f'{{"userId":"{handle_id}",'
                     '"count":10,'
                     '"includePromotedContent":false,'
                     '"withQuickPromoteEligibilityTweetFields":false,'
                     '"withVoice":true,'
                     '"withV2Timeline":true}',
        "features": '{"rweb_lists_timeline_redesign_enabled": true,'
                     '"responsive_web_graphql_exclude_directive_enabled": false,'
                     '"verified_phone_label_enabled": false,'
                     '"creator_subscriptions_tweet_preview_api_enabled": true,'
                     '"responsive_web_graphql_timeline_navigation_enabled": true,'
                     '"responsive_web_graphql_skip_user_profile_image_extensions_enabled": false,'
                     '"tweetypie_unmention_optimization_enabled": true,'
                     '"responsive_web_edit_tweet_api_enabled": true,'
                     '"graphql_is_translatable_rweb_tweet_is_translatable_enabled": true,'
                     '"view_counts_everywhere_api_enabled": true,'
                     '"longform_notetweets_consumption_enabled": true,'
                     '"responsive_web_twitter_article_tweet_consumption_enabled": false,'
                     '"tweet_awards_web_tipping_enabled": false,'
                     '"freedom_of_speech_not_reach_fetch_enabled": false,'
                     '"standardized_nudges_misinfo": true,'
                     '"tweet_with_visibility_results_prefer_gql_limited_actions_policy_enabled": false,'
                     '"longform_notetweets_rich_text_read_enabled": true,'
                     '"longform_notetweets_inline_media_enabled": true,'
                     '"responsive_web_media_download_video_enabled": false,'
                     '"responsive_web_enhance_cards_enabled": false}'
    }
    try:
        rest_id_response = requests.get(url=space_id_url, headers=headers, cookies=cookies, params=params, timeout=10)
    except (requests.exceptions.ConnectionError, requests.exceptions.RetryError, requests.exceptions.ReadTimeout) as r_exception:
        logger.debug(r_exception)
        logger.debug(f"[{handle_name}] Connection issue occurred while looking for twitter space...")
        return None
    except requests.exceptions.RequestException as req_exceptions:
        logger.error(f"[{handle_name}] {req_exceptions}", exc_info=True)
        return None
    except Exception as e:
        logger.error(e, exc_info=True)
        return None

    # Error check
    if rest_id_response.status_code != 200:
        try:
            rest_id_json = rest_id_response.json()
        except requests.exceptions.JSONDecodeError:
            logger.debug(f"[{handle_name}] JSONDecodeError: {rest_id_response}", exc_info=True)
            logger.debug(f"[{handle_name}] JSONDecodeError: {rest_id_response.headers}")
            logger.warning(
                f"[{handle_name}] Issue finding space with error code {rest_id_response.status_code} {rest_id_response.text.strip()}")
            if rest_id_response.status_code == 429:
                logger.debug(f"[{handle_name}] JSONDecodeError: {rest_id_response.headers}")
                handle_rate_limit(handle_name, rest_id_response.headers, logger=logger)
            return None

        try:
            # try except so script can work after a long period of inactivity(sleep)
            if 'error' in rest_id_json or 'errors' in rest_id_json:
                logger.debug(f"[{handle_name}] {rest_id_json}")
                if isinstance(rest_id_json.get('errors'), list):
                    logger.debug(f"[{handle_name}] {rest_id_json} Error {rest_id_json['errors'][0]['code']} {rest_id_json['errors'][0]['message']}")
                    # Needed anymore?
                    if rest_id_json['errors'][0]['code'] == 88:
                        handle_rate_limit(handle_name, rest_id_response.headers, logger=logger)
                elif rest_id_json.get('errors').get(0).get('code') == 239:
                    logger.debug(
                        f"[{handle_name}] Issue finding space with error code {rest_id_response.status_code} {rest_id_response.text.strip()}")
                    logger.debug(f"[{handle_name}] JSONDecodeError: {rest_id_response.headers}")
                elif rest_id_json.get('errors').get(0).get('code') in (32, 353):
                    logger.error(
                        f"[{handle_name}] Issue finding space, may need to get new tokens with error code {rest_id_response.status_code} {rest_id_response.text.strip()}")
                    logger.debug(f"[{handle_name}] JSONDecodeError: {rest_id_response.headers}")
                else:
                    logger.error(
                        f"[{handle_name}] Issue finding space, may need to get new tokens with error code {rest_id_response.status_code} {rest_id_response.json().get('errors').get(0).get('message')}")
        except AttributeError as aError:
            logger.debug(aError, exc_info=True)

        else:
            logger.warning(f"[{handle_name}] Issue finding space with error code {rest_id_response.status_code} {rest_id_response.text.strip()}")
    elif 'data' not in rest_id_response.json():
        logger.debug(f"[{handle_name}] {rest_id_response}")
    handle_rate_limit(handle_name, rest_id_response.headers, logger=logger)

    # space_id = space_id_response.json()['data']['user']['result']['timeline_v2']['timeline']['instructions'][0]['entries'][0]['result']['legacy']['extended_entities']['media']['media_key']
    rest_id = None
    try:
        rest_id = re.search(string=rest_id_response.text, pattern=space_id_pattern).group(1)
        logger.debug(f"Space ID for {handle_name}({handle_id}): {rest_id}")
    except AttributeError:
        # No space found
        return rest_id

    return rest_id


# Gets detailed information/status of the twitter space
# Returns a media key which is used to get information about the video stream(m3u8 url)
def get_space_details(handle_name, rest_id, logger=None):
    logger = set_logger(logger)

    # See AudioSpaceById for example json response
    space_id_url = "https://twitter.com/i/api/graphql/kZ9wfR8EBtiP0As3sFFrBA/AudioSpaceById"
    headers = {"Authorization": BEARER_TOKEN, "X-Csrf-Token": CSRF_TOKEN}
    cookies = {"auth_token": AUTH_TOKEN, "ct0": CSRF_TOKEN}

    params = {
        "variables": f'{{"id":"{rest_id}",'
                     '"isMetatagsQuery":false,'
                     '"withListeners":true,'
                     '"withReplays":true}',
        "features": '{"spaces_2022_h2_clipping":true,'
                     '"spaces_2022_h2_spaces_communities":true,'
                     '"responsive_web_graphql_exclude_directive_enabled":false,'
                     '"verified_phone_label_enabled":false,'
                     '"creator_subscriptions_tweet_preview_api_enabled":true,'
                     '"responsive_web_graphql_skip_user_profile_image_extensions_enabled":false,'
                     '"tweetypie_unmention_optimization_enabled":true,'
                     '"responsive_web_edit_tweet_api_enabled":true,'
                     '"graphql_is_translatable_rweb_tweet_is_translatable_enabled":true,'
                     '"view_counts_everywhere_api_enabled":true,'
                     '"longform_notetweets_consumption_enabled":true,'
                     '"responsive_web_twitter_article_tweet_consumption_enabled":false,'
                     '"tweet_awards_web_tipping_enabled":false,'
                     '"freedom_of_speech_not_reach_fetch_enabled":true,'
                     '"freedom_of_speech_not_reach_appeal_label_enabled":false,'
                     '"standardized_nudges_misinfo":true,'
                     '"tweet_with_visibility_results_prefer_gql_limited_actions_policy_enabled":true,'
                     '"responsive_web_graphql_timeline_navigation_enabled":true,'
                     '"longform_notetweets_rich_text_read_enabled":true,'
                     '"longform_notetweets_inline_media_enabled":true,'
                     '"responsive_web_media_download_video_enabled":false,'
                     '"responsive_web_enhance_cards_enabled":false}'
    }
    try:
        space_id_response = requests.get(url=space_id_url, headers=headers, cookies=cookies, params=params, timeout=10)
    except (requests.exceptions.ConnectionError, requests.exceptions.RetryError, requests.exceptions.ReadTimeout) as r_exception:
        logger.debug(r_exception)
        logger.debug(f"[{handle_name}] Connection issue occurred while looking for twitter space...")
        return None
    except requests.exceptions.RequestException as req_exceptions:
        logger.error(f"[{handle_name}] {req_exceptions}", exc_info=True)
        return None
    except Exception as e:
        logger.error(e, exc_info=True)
        return None
    # Error check
    try:
        space_id_json = space_id_response.json()
        logger.debug(f"[{handle_name}] Space Details: {space_id_json}")
        logger.debug(f"[{handle_name}] Space ID Json Headers: {space_id_response.headers}")
    except requests.exceptions.JSONDecodeError:
        logger.error(f"[{handle_name}] Issue getting space details with error code {space_id_response.status_code} {space_id_response.text.strip()}")
        logger.debug(space_id_response)
        return None

    if space_id_response.status_code == 429:
        handle_rate_limit(handle_name, space_id_response.headers, logger=logger)
        logger.debug(f"[{handle_name}] Error {space_id_response.status_code} {space_id_response.text}", exc_info=True)

    if 'data' not in space_id_json or space_id_response.status_code != 200:
        if 'error' in space_id_json:
            # Not needed anymore?
            if space_id_json['errors'][0]['code'] in (32, 353):
                logger.info(f"[{handle_name}] Bad guest token, renewing...")
                logger.error(
                    f"[{handle_name}] Issue finding space, may need to get new tokens with error code {space_id_json.status_code} {space_id_json.text.strip()}")
            logger.error(f"[{handle_name}] Issue getting media key with error code {space_id_response.status_code} {space_id_json}")
            return None
        else:
            # {'data': {'audioSpace': {}}}
            logger.debug("Empty object received...")
            return None
    elif space_id_json.get('data').get('audioSpace') == {}:
        # {'data': {'audioSpace': {}}}
        return None

    handle_rate_limit(handle_name, space_id_response.headers, logger=logger)
    return space_id_response


def get_media_key(handle_name, space_detail, logger=None):
    logger = set_logger(logger)
    media_key = None
    # media_key_pattern = r'"media_key":"(.*?)"'
    # space_id = space_id_response.json()['data']['user']['result']['timeline_v2']['timeline']['instructions'][0]['entries'][0]['result']['legacy']['extended_entities']['media']['media_key']
    try:
        # media_key = re.search(string=space_detail.text, pattern=media_key_pattern).group(1)
        media_key = space_detail['media_key']
        logger.debug(f"[{handle_name}] Media Key: {media_key}")
    except (AttributeError, KeyError):
        logger.error(f"[{handle_name}] Issue finding media key")
        logger.debug(f"[{handle_name}] {space_detail}")
    return media_key


# Gets detailed information about the video/media stream
# Returns m3u8 url
def get_space_source(handle_name, media_key, logger=None):
    logger = set_logger(logger)
    location_url = None
    # See live_video_stream for example json response
    space_source_url = f"https://api.twitter.com/1.1/live_video_stream/status/{media_key}"
    headers = {"Authorization": BEARER_TOKEN}
    try:
        space_source_response = requests.get(url=space_source_url, headers=headers, timeout=10)
    except (requests.exceptions.RequestException, urllib3.exceptions.MaxRetryError, requests.exceptions.RetryError) as e:
        logger.error(f"[{handle_name}] {e}")

    if space_source_response.status_code != 200:
        logger.error(f"[{handle_name}] Issue getting space source with error code {space_source_response.status_code}")
        logger.debug(f"[{handle_name}] Space Source Headers: {space_source_response.headers}")
        handle_rate_limit(handle_name, space_source_response.headers, logger=logger)
        return location_url

    space_source = space_source_response.json()
    location_url = space_source["source"]["location"].replace("dynamic", "master").replace("?type=live", "")
    logger.debug(f"[{handle_name}] Space Source: {space_source}")

    return location_url


def create_users():
    for user in twitter_ids:
        user_name, user_id = user.popitem()
        TwitterSpaces[user_id] = TwitterSpace(handle_id=str(user_id), handle_name=user_name)


def get_spaces(logger=None):
    for user in TwitterSpaces.values():
        time.sleep(SLEEP_TIME)
        logger.debug(f"[{user.handle_name}] Looking for spaces...")
        try:
            rest_id = get_space_tweet_id(user.handle_id, user.handle_name, logger=logger)
            if rest_id is None:
                # logger.debug(f"{user.handle_name} is currently offline...")
                continue
            try:
                time.sleep(SLEEP_TIME)
                space_details_res = get_space_details(user.handle_name, rest_id, logger=logger)
            except Exception as e:
                logger.error(e, exc_info=True)

            if space_details_res is None:
                logger.debug(f"[{user.handle_name}] Unable to get space details...")
                continue
            else:
                space_details = space_details_res.json()['data']['audioSpace']['metadata']
                logger.debug(f"[{user.handle_name}] {space_details_res.json()}")
                # If space has already been queried or is a past space that has not been queried then skip
                if user.space_state == space_details['state'] or user.space_state is None and space_details['state'] == 'Ended':
                    logger.debug(f"[{user.handle_name}] Past space, skipping...")
                    continue

                # Handling new spaces
                if user.space_state == 'Ended' and space_details['state'] == 'Running':
                    user.reset_default()
                    logger.debug(f"Resetting default values for {user.handle_name}")

                # Handling scheduled space
                if user.space_state == 'NotStarted' and space_details['state'] == 'Running':
                    user.reset_default()
                    logger.info(f"Scheduled space from {user.handle_name} is now live")
                    logger.debug(f"Resetting default values for {user.handle_name}")

            try:
                space_creator_id, space_creator_name, participant_title = get_space_participant(user, space_details_res)
            except (KeyError, requests.exceptions.JSONDecodeError) as cError:
                logger.debug(cError)
                space_creator_id, space_creator_name, participant_title = user.space_creator_id, user.handle_name, None

            # TODO: Add another check to not track space if it's a retweeted where host is also on the list
            # If current user isn't hosting the space or participating and should not be tracked
            # if user.handle_id != space_creator_id and participant_title is None and not ALL_SPACE_TIMELINE:
            #     continue

            user.rest_id = rest_id
            media_key = get_media_key(user.handle_name, space_details, logger=logger)
            user.media_key = media_key
            user.set_space_details(space_details)
            user.space_creator_id = space_creator_id
            user.space_creator_name = space_creator_name
            user.space_participant_title = participant_title
            logger.debug(f"[{user.handle_name}] {space_details}")

            try:
                if user.space_state == "Running" and not user.space_notified:
                    notify_space(user)
            except Exception as e:
                logger.error(f"[{user.handle_name}] Issue notifying space", exc_info=True)
                logger.debug(e, exc_info=True)

        except Exception as e:
            logger.error(f"[{user.handle_name}] Issue getting latest space id", exc_info=True)
            logger.debug(e, exc_info=True)
            continue


def download(ended_spaces, logger=None):
    if DOWNLOAD is not None or False:
        downloaded = []
        for ended_space in ended_spaces:
            # if int(ended_space.space_duration) == 0:
            #     duration = datetime.timestamp(datetime.now()) - ended_space.space_started_at/1000.0
            #     ended_space.space_duration = duration
            #     logger.debug(f"Setting custom duration of {duration} for {ended_space.handle_name}")

            # ended_space.m3u8_url = get_space_source(media_key=ended_space.media_key, logger=logger)
            # print(" " * 70, end='\n')

            # Add a check to avoid duplicate download for retweeted/joined space between two or more tracked user
            if ended_space.rest_id in downloaded:
                logger.warning(f"[{ended_space.handle_name}] {ended_space.rest_id} has already been downloaded, skipping...")
                ended_space.space_downloaded = True
                continue

            logger.info(f"{ended_space.space_creator_name} is now offline at {ended_space.rest_id}")

            try:
                if ended_space.m3u8_url is None:
                    ended_space.m3u8_url = get_space_source(handle_name=ended_space.space_creator, media_key=ended_space.media_key, logger=logger)
                    if ended_space.m3u8_url is None:
                        logger.error(
                            f"[{ended_space.handle_name}] Can not download space for {ended_space.space_creator_name}, unable to find m3u8 url...")
                        return

                ended_space.set_space_duration()
                server = ended_space.get_server()
                m3u8_id = ended_space.get_m3u8_id()
                space_date = ended_space.get_strftime()
                logger.debug(ended_space)
                threading.Thread(target=twspace.download,
                                 args=[m3u8_id, ended_space.rest_id, ended_space.space_creator_name,
                                       ended_space.handle_name, ended_space.space_title, server,
                                       ended_space.space_duration, space_date, logger]).start()
                ended_space.space_downloaded = True
                downloaded.append(ended_space.rest_id)
            except Exception as thread_exception:
                logger.error(thread_exception, exc_info=True)
                ended_space.space_downloaded = False


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


def notify_space(space):
    logger.debug(f"{[space.space_creator_name]} Space Object: {str(space)}")
    # logger.debug(f"Space Details: {str(space[0]['data'])}")
    # logger.debug(f"User Details: {str(space[1]['data'])}")
    space_id = space.rest_id
    status = 'live' if space.space_state == 'Running' else space.space_state
    creator_profile_image = space.handle_image

    space_creator = space.space_creator_name
    space_handle_name = space.handle_name
    space_started_at = space.get_strftime()
    space_title = space.space_title

    space_url = f"https://twitter.com/i/spaces/{space_id}"

    # Get and send the m3u8 url
    counter = 0
    m3u8_url = None
    while counter <= 5:
        m3u8_url = get_space_source(handle_name=space_creator, media_key=space.media_key, logger=logger)
        if m3u8_url is None:
            counter += 1
            time.sleep(SLEEP_TIME)
            logger.warning(f"[{space.handle_name}]Retrying to get m3u8 url {counter}/{5}")
            continue
        else:
            break

    space.m3u8_url = m3u8_url
    logger.debug(space)
    # Todo maybe consider changing space_creator to `space_creator` to avoid underscore error
    if space.handle_id == space.space_creator_id:
        logger.info(f"{space_creator} is now {status} at {space_url}")
    else:
        logger.info(f"{space_handle_name} is participating at {space_url}")
    logger.info(f"M3U8: {m3u8_url}")

    if space.handle_id == space.space_creator_id:
        description = f"{space_creator} is now {status} at <{space_url}> ```{m3u8_url}```"
    else:
        description = f"{space_handle_name} is participating at <{space_url}> ```{m3u8_url}```"
    message = {"embeds": [{
        "color": 1942002,
        "author": {
            "name": f"{space_creator}",
            "icon_url": creator_profile_image
        },
        "fields": [
            {
                "name": space_title,
                "value": description
            }
        ],
        "thumbnail": {
            "url": creator_profile_image.replace("normal", "200x200")
        }
    }]
    }
    if WEBHOOK_URL is not None:
        requests.post(WEBHOOK_URL, json=message)
    space.space_notified = True


if __name__ == "__main__":
    logger = create_logger("logfile.log")
    logger.info("Starting program")
    threading.Thread(target=loading_text).start()
    # session = create_session()
    # loading_string = "[INFO] Waiting for live twitter spaces"
    create_users()

    while True:
        try:
            get_spaces(logger=logger)
            # space_list = [space for space in TwitterSpaces.values() if space.space_state == "Running" and not space.space_notified]
            to_download = [space for space in TwitterSpaces.values() if space.space_state == "Ended" and not space.space_downloaded and space.space_was_running]

            # if space_list is None:
            #     continue

            # Download spaces that have ended and have yet to be downloaded
            if to_download is not None:
                download(to_download, logger=logger)

        except SystemExit:
            sys.exit("Error, Exiting")
        except OSError:
            sys.exit("Error, Exiting")
        except KeyboardInterrupt:
            sys.exit("Error, Exiting")
        except Exception as e:
            logger.error(e, exc_info=True)
