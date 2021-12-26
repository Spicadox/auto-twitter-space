import discord
import time
import asyncio
import tweepy
from dotenv import dotenv_values
import xhr_grabber

config = dotenv_values(".env")

EXPIRE_TIME = int(config["EXPIRE_TIME"])
SLEEP_TIME = int(config["SLEEP_TIME"])

api_key = config["api_key"]
api_key_secret = config["api_key_secret"]
bearer_token = config["bearer_token"]
access_token = config["access_token"]
access_token_secret = config["access_token_secret"]
WEBHOOK_AUTH_TOKEN = config["WEBHOOK_AUTH_TOKEN"]
WEBHOOK_ID = int(config["WEBHOOK_ID"])
DISCORD_TOKEN = config["DISCORD_TOKEN"]

# Authorize and setup twitter client
auth = tweepy.OAuthHandler(api_key, api_key_secret)
auth.set_access_token(access_token, access_token_secret)
api = tweepy.API(auth)
twitter_client = tweepy.Client(bearer_token, consumer_key=api_key, consumer_secret=api_key_secret, access_token=access_token, access_token_secret=access_token_secret)

# Gamers IDs
discord_ids = [{"inugamikorone": 1109748792721432577}, {"nekomataokayu": 1109751762733301760},
               {"ookamimio": 1063337246231687169}, {"shirakamifubuki": 997786053124616192}]
# Gen 0 IDs
discord_ids += [{'tokino_sora': 880317891249188864}, {'robocosan': 960340787782299648}, {'sakuramiko35': 979891380616019968},
                {'suisei_hosimati': 975275878673408001}, {'AZKi_VDiVA': 1062499145267605504}]
# Gen 1 IDs
discord_ids += [{'yozoramel':  985703615758123008}, {'akirosenthal': 996643748862836736},
                {'akaihaato': 998336069992001537}, {'natsuiromatsuri': 996645451045617664}]
# Gen 2 IDs
discord_ids += [{'minatoaqua': 1024528894940987392}, {'murasakishionch': 1024533638879166464}, {'nakiriayame': 1024532356554608640},
                {'yuzukichococh': 1024970912859189248}, {'oozorasubaru': 1027853566780698624}]
# Gen 3 IDs
discord_ids += [{'houshoumarine': 1153192638645821440}, {'shiroganenoel': 1153195295573856256}, {'shiranuiflare': 1154304634569150464},
                {'uruharushia': 1142975277175205888}, {'usadapekora': 1133215093246664706}]
# Gen 4 IDs
discord_ids += [{'himemoriluna': 1200396798281445376}, {'amanekanatach': 1200396304360206337},
                {'tokoyamitowa': 1200357161747939328}, {'tsunomakiwatame': 1200397643479805957}]
# Gen 5 IDs
discord_ids += [{'omarupolka': 1270551806993547265}, {'yukihanalamy': 1255013740799356929},
                {'shishirobotan': 1255015814979186689}, {'momosuzunene': 1255017971363090432}]
# Gen 6 IDs
discord_ids += [{'LaplusDarknesss': 1433657158067896325}, {'takanelui': 1433660866063339527}, {'hakuikoyori': 1433667543806267393},
                {'sakamatachloe': 1433667543806267393}, {'kazamairohach': 1434755250049589252}]
# Other IDs
discord_ids += [{'ksononair':  733990222787018753}]

space_fields = ['creator_id', 'id', 'title', 'topic_ids', 'started_at']
expansions = ['creator_id', 'host_ids' ]

twitter_id_list = []
for user in discord_ids:
    twitter_id_list.append(str(*user.values()))

user_ids = ",".join(twitter_id_list)


client = discord.Client()
notified_spaces = []


def get_spaces():
    try:
        req = twitter_client.get_spaces(user_ids=twitter_id_list, expansions=expansions)
    except Exception as e:
        print(f"[error] {e}")
        return []
    # response example
    # Response(data=[<Space id=1vOGwyQpQAVxB state=live>, <Space id=1ypKdEePLXLGW state=live>], includes={'users': [<User id=838403636015185920 name=Misaネキ username=Misamisatotomi>, <User id=1181889913517572096 name=アステル・レダ🎭 / オリジナルソングMV公開中!! username=astelleda>]}, errors=[], meta={'result_count': 2})
    space_list = []
    result_count = req[3]["result_count"]
    if result_count != 0:
        datas = req[0]
        users = req[1]["users"]
        for data, user in zip(datas, users):
            space_list.append([data, user])
    return space_list


@client.event
async def on_ready():
    print("We have logged in as {0.user}".format(client))

    # Bot
    # channel = client.get_channel(922987834044981269)
    # await channel.send("IM HERE")

    # Initialize Webhook
    # Not an alternative to all of this is just use requests to post to webhook url
    webhook = discord.Webhook.partial(WEBHOOK_ID, WEBHOOK_AUTH_TOKEN, adapter=discord.RequestsWebhookAdapter())
    while True:
        space_list = get_spaces()
        start_time = time.time()
        expire_time = EXPIRE_TIME
        # Remove expired spaces from list to free up memory
        if time.time() - start_time > expire_time and len(notified_spaces) != 0:
            notified_spaces.remove(notified_spaces[0])
            start_time = time.time()

        # Get and send out space url and m3u8 to discord webhook
        for space in space_list:
            if len(space_list) != 0:
                space_id = space[0]["id"]
                if space_id not in notified_spaces:
                    status = space[0]["state"]
                    space_creator = space[1]
                    space_url = f"https://twitter.com/i/spaces/{space_id}"

                    # Webhook that sends the space url
                    print(f"[info] `{space_creator}` is now `{status}` at `{space_url}`")
                    webhook.send(f"`{space_creator}` is now `{status}` at `{space_url}`")

                    # Get and send the m3u8 url
                    m3u8_url = xhr_grabber.get_m3u8(space_url)
                    if m3u8_url is not None:
                        print(f"[info] `{space_creator}` at `{space_url}` M3U8: ```{m3u8_url}```")
                        webhook.send(f"`{space_creator}` at `{space_url}` M3U8: ```{m3u8_url}```")
                        notified_spaces.append(space_id)
            else:
                print(f"[info] No Spaces, Sleeping for {SLEEP_TIME} secs...")
        print(f"[info] Sleeping for {SLEEP_TIME} secs...")
        await asyncio.sleep(SLEEP_TIME)
    return webhook

client.run(DISCORD_TOKEN)
