import time
import tweepy
import xhr_grabber
import requests
import twspace
import threading
import re
import subprocess
import const

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

# Gamers IDs
discord_ids = [{"inugamikorone": 1109748792721432577}, {"nekomataokayu": 1109751762733301760},
               {"ookamimio": 1063337246231687169}, {"shirakamifubuki": 997786053124616192}]
# Gen 0 IDs
discord_ids += [{'tokino_sora': 880317891249188864}, {'robocosan': 960340787782299648},
                {'sakuramiko35': 979891380616019968},
                {'suisei_hosimati': 975275878673408001}, {'AZKi_VDiVA': 1062499145267605504}]
# Gen 1 IDs
discord_ids += [{'yozoramel': 985703615758123008}, {'akirosenthal': 996643748862836736},
                {'akaihaato': 998336069992001537}, {'natsuiromatsuri': 996645451045617664}]
# Gen 2 IDs
discord_ids += [{'minatoaqua': 1024528894940987392}, {'murasakishionch': 1024533638879166464},
                {'nakiriayame': 1024532356554608640},
                {'yuzukichococh': 1024970912859189248}, {'oozorasubaru': 1027853566780698624}]
# Gen 3 IDs
discord_ids += [{'houshoumarine': 1153192638645821440}, {'shiroganenoel': 1153195295573856256},
                {'shiranuiflare': 1154304634569150464},
                {'uruharushia': 1142975277175205888}, {'usadapekora': 1133215093246664706}]
# Gen 4 IDs
discord_ids += [{'himemoriluna': 1200396798281445376}, {'amanekanatach': 1200396304360206337},
                {'tokoyamitowa': 1200357161747939328}, {'tsunomakiwatame': 1200397643479805957}]
# Gen 5 IDs
discord_ids += [{'omarupolka': 1270551806993547265}, {'yukihanalamy': 1255013740799356929},
                {'shishirobotan': 1255015814979186689}, {'momosuzunene': 1255017971363090432}]
# Gen 6 IDs
discord_ids += [{'LaplusDarknesss': 1433657158067896325}, {'takanelui': 1433660866063339527},
                {'hakuikoyori': 1433667543806267393},
                {'sakamatachloe': 1433667543806267393}, {'kazamairohach': 1434755250049589252}]
# Other IDs
discord_ids += [{'ksononair': 733990222787018753}, {'tanigox': 2006101}, {'achan_UGA': 1064352899705143297},
                {'daidoushinove': 1156797715319160832}, {"kotone": 986871577890312192}]

# Holostars Gen 1 IDs
discord_ids += [{'miyabihanasaki': 1132832428353966081}, {'arurandeisu': 1156841498479955968},
                {'rikkaroid': 1174223248655114246}, {'kanadeizuru': 1132924263441227776}]
# Holostars Gen 2 SunTempo IDs
discord_ids += [{'kishidotemma': 1194519616472543232}, {'astelleda': 1181889913517572096},
                {'yukokuroberu': 1194520283446530051}]
# Holostars Gen 3 MaFia IDs
discord_ids += [{'kageyamashien': 1248565757207695361}, {'aragamioga': 1248567107173773313}]

# HoloID Gen 1 IDs
discord_ids += [{'ayunda_risu': 1234752200145899520}, {'moonahoshinova': 1234753886520393729},
                {'airaniiofifteen': 1235180878449397764}]

# HoloID Gen 2 IDs
discord_ids += [{'anyamelfissa': 1328277750000492545}, {'kureijiollie': 1328277233492844544},
                {'pavoliareine': 1328275136575799297}]

# HoloEN Gen 1 Myth IDs
discord_ids += [{'moricalliope': 1283653858510598144}, {'takanashikiara': 1283646922406760448},
                {'ninomaeinanis': 1283650008835743744}]
discord_ids += [{'gawrgura': 1283657064410017793}, {'watsonameliaEN': 1283656034305769472}]

# HoloEN Project Hope ID
discord_ids += [{'irys_en': 1363705980261855232}]

# HoloEN Gen 2 Council IDs
discord_ids += [{'tsukumosana': 1409819816194576394}, {'ceresfauna': 1409784760805650436},
                {'ourokronii': 1409817096523968513}]
discord_ids += [{'nanashimumei_en': 1409817941705515015}, {'hakosbaelz': 1409783149211443200}]

space_fields = ['id', 'state', 'title', 'started_at']
user_fields = ['profile_image_url']
expansions = ['creator_id', 'host_ids']

twitter_id_list = []
for twitter_user in discord_ids:
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
        # Use default command if download output is not specified
        if RYU_DOWNLOAD:
            command_list = ["twspace_dl.exe", "-i", f"https://twitter.com/i/spaces/{notified_space_id}"]
            command_list += ['-f', notified_space_m3u8_id]
        else:
            command_list = ["twspace_dl.exe", "-i", f"https://twitter.com/i/spaces/{notified_space_id}"]
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
                    space_started_at = space[0].started_at.strftime("%Y%m%d")
                    space_title = space[0].title
                    space_url = f"https://twitter.com/i/spaces/{space_id}"

                    # Get and send the m3u8 url
                    m3u8_url = xhr_grabber.get_m3u8(space_url)
                    if m3u8_url is not None:
                        print(f"[info] {space_creator} is now {status} at {space_url} \n[info] M3U8: {m3u8_url}")
                        # message = {'content': f"`{space_creator}` is now `{status}` at {space_url} ```{m3u8_url}```"}
                        message = {"embeds": [{
                            "author": {
                                "name": f"{space_creator} Is Live",
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
