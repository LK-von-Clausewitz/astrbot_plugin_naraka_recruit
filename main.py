import time
from collections import defaultdict
from astrbot.api.event import filter, AstrMessageEvent
from astrbot.api.star import Context, Star, register
from astrbot.api import logger
@register(
    "astrbot_plugin_naraka_recruit",
    "LK-von-Clausewitz",
    "永劫无间小劫宝专属：@小劫宝 双排/三排/娱乐组队",
    "1.0.0",
    "https://github.com/LK-von-Clausewitz/astrbot_plugin_naraka_recruit"
)
class NarakaRecruitPlugin(Star):
    def __init__(self, context: Context):
        super().__init__(context)
        self.cooldown = {}
        self.daily_count = defaultdict(lambda: defaultdict(int))
        self.cooldown_seconds = 30
        self.daily_limit = 3
        self.bot_nicknames = ["小劫宝"]

    async def _send_group_message(self, event: AstrMessageEvent, message_chain: list) -> bool:
        try:
            request_data = {
                "action": "send_group_msg",
                "params": {
                    "group_id": event.message_obj.group_id,
                    "message": message_chain
                }
            }
            response = await event.platform.sapi.send_request(request_data)
            if response and response.get('status') == 'ok':
                return True
            logger.error(f"发送消息失败, 响应: {response}")
            return False
        except Exception as e:
            logger.error(f"调用发送消息API时发生异常: {e}")
            return False

    def _is_rate_limited(self, user_id: str) -> tuple[bool, str]:
        now = time.time()
        if user_id in self.cooldown:
            elapsed = now - self.cooldown[user_id]
            if elapsed < self.cooldown_seconds:
                wait = int(self.cooldown_seconds - elapsed)
                return True, f"操作过于频繁，请等待 {wait} 秒后再试。"
        today = time.strftime("%Y-%m-%d")
        if self.daily_count[user_id][today] >= self.daily_limit:
            return True, f"您今天已经使用了 {self.daily_limit} 次招募机会，请明天再来。"
        return False, ""

    def _record_usage(self, user_id: str):
        self.cooldown[user_id] = time.time()
        today = time.strftime("%Y-%m-%d")
        self.daily_count[user_id][today] += 1

    @filter.regex(r"^\s*双排组队\s*$")
    async def recruit_double(self, event: AstrMessageEvent):
        for nickname in self.bot_nicknames:
            if nickname in event.message_str:
                yield await self._handle_recruit(event, "双排")
                return

    @filter.regex(r"^\s*三排组队\s*$")
    async def recruit_triple(self, event: AstrMessageEvent):
        for nickname in self.bot_nicknames:
            if nickname in event.message_str:
                yield await self._handle_recruit(event, "三排")
                return

    @filter.regex(r"^\s*娱乐组队\s*$")
    async def recruit_casual(self, event: AstrMessageEvent):
        for nickname in self.bot_nicknames:
            if nickname in event.message_str:
                yield await self._handle_recruit(event, "娱乐")
                return

    async def _handle_recruit(self, event: AstrMessageEvent, mode: str):
        sender_id = event.get_sender_id()
        sender_name = event.get_sender_name()

        limited, msg = self._is_rate_limited(sender_id)
        if limited:
            return event.plain_result(f"❌ {msg}")

        at_all_segment = {
            "type": "at",
            "data": {"qq": "all"}
        }
        text_content = (
            f"🔥【永劫无间 {mode} 招募】🔥\n"
            f"发起人：{sender_name}（{sender_id}）\n"
            f"模式：{mode}\n\n"
            f"感兴趣的朋友请直接联系发起人！速速上车！"
        )
        text_segment = {
            "type": "text",
            "data": {"text": text_content}
        }
        message_chain = [at_all_segment, text_segment]

        success = await self._send_group_message(event, message_chain)
        if success:
            self._record_usage(sender_id)
            return event.plain_result("✅ 小劫宝已帮你发布招募并@全体成员！")
        else:
            return event.plain_result("❌ 发布失败，请确保小劫宝是群管理员且@全体成员次数未达上限。")

    async def terminate(self):
        logger.info("永劫无间小劫宝招募插件已卸载。")
