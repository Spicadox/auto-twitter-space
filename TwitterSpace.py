import dataclasses
from datetime import datetime
import re


@dataclasses.dataclass
class TwitterSpace:
    handle_id: str
    handle_name: str
    handle_image: str = None
    space_title: str = "Twitter Space"
    space_state: str = None
    space_creator_id: str = None
    space_participant_title: str = None  # admin or speaker
    space_was_running: bool = False
    space_started_at: int = 0
    space_ended_at: int = 0
    space_url: str = None
    m3u8_url: str = None
    space_notified: bool = False
    space_downloaded: bool = False
    space_duration: float = 0
    rest_id: str = None
    media_key: str = None

    def get_strftime(self):
        # initial timestamp is in milliseconds and not seconds
        return datetime.fromtimestamp(self.space_started_at/1000).strftime("%Y%m%d")

    def get_m3u8_id(self):
        return re.search("(.*\/Transcoding\/v1\/hls\/(.*)(\/non_transcode.*))", self.m3u8_url).group(2)

    def get_server(self):
        print(self.m3u8_url)
        reg_result = re.search("(https:\/\/)((?:[^-]*-){2})(.*)(\.pscp.*)", self.m3u8_url)
        # regex will return something like 'prod-fastly-' so remove the last dash
        deployment_server = reg_result.group(2)[:-1]
        periscope_server = reg_result.group(3)
        server = (deployment_server, periscope_server)
        return server

    def set_space_duration(self):
        self.space_duration = self.space_ended_at/1000.0 - self.space_started_at/1000.0

    # def set_server(self):
    #     reg_result = re.search("(https:\/\/)((?:[^-]*-){2})(.*)(\.pscp.*)", self.m3u8_url)
    #     # regex will return something like 'prod-fastly-' so remove the last dash
    #     self.deployment_server = reg_result.group(2)[:-1]
    #     self.periscope_server = reg_result.group(3)

    def set_space_details(self, space_details):
        self.handle_image = space_details['creator_results']['result']['legacy']['profile_image_url_https']
        self.space_title = space_details['title']
        self.space_started_at = space_details['started_at']
        self.space_state = space_details['state']
        self.space_was_running = True
        self.space_ended_at = space_details.get('ended_at', 0)

    def reset_default(self):
        self.handle_id: str = self.handle_id
        self.handle_name: str = self.handle_name
        self.handle_image: str = None
        self.space_title: str = None
        self.space_state: str = None
        self.is_space_creator: bool = False
        self.space_participant_title: str = None
        self.space_was_running: bool = False
        self.space_started_at: int = 0
        self.space_ended_at: int = 0
        self.space_url: str = None
        self.m3u8_url: str = None
        self.space_notified: bool = False
        self.space_downloaded: bool = False
        self.space_duration: float = 0
        self.rest_id: str = None
        self.media_key: str = None


