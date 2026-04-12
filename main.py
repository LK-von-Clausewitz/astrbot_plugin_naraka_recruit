import time
from collections import defaultdict
from astrbot.api.event import filter, AstrMessageEvent
from astrbot.api.star import Context, Star, register
from astrbot.api import logger
# 导入正确的组件
from astrbot.api.message_components import AtAll, Plain

@register(
    "astrbot_plugin_naraka_recruit",
    "LK-von-Clausewitz",
    "永劫无间组队：AtAll 标准版",
    "1.0.7",
    "https://github.com/LK-von-Clausewitz/astrbot_plugin_naraka_recruit"
)
class NarakaRecruitPlugin(Star):
    def __init__(self, context: Context):
        super().__init__(context)
        self.cooldown = {}
        self.daily_count = defaultdict(lambda: defaultdict(int))
        self.cooldown_seconds = 30
        self.daily_limit = 3
        self.bot_nickname = "小劫宝"

    @filter.regex(r"双排组队")
    async def recruit_double(self, event: AstrMessageEvent):
        if self._check_if_called(event):
            return await self._handle_recruit(event, "双排")

    @filter.regex(r"三排组队")
    async def recruit_triple(self, event: AstrMessageEvent):
        if self._check_if_called(event):
            return await self._handle_recruit(event, "三排")

    @filter.regex(r"娱乐组队")
    async def recruit_casual(self, event: AstrMessageEvent):
        if self._check_if_called(event):
            return await self._handle_recruit(event, "娱乐")

    def _check_if_called(self, event: AstrMessageEvent) -> bool:
        msg_str = event.message_str
        if self.bot_nickname in msg_str:
            return True
        try:
            for seg in event.message_obj.message:
                if seg.get("type") == "at":
                    return True
        except:
            pass
        return False

    async def _handle_recruit(self, event: AstrMessageEvent, mode: str):
        sender_id = event.get_sender_id()
        sender_name = event.get_sender_name()

        limited, msg = self._is_rate_limited(sender_id)
        if limited:
            return event.plain_result(f"❌ {msg}")

        # 重点：不再手写 CQ 码，使用 AtAll() 组件
        text_content = (
            f"\n🔥【永劫无间 {mode} 招募】🔥\n"
            f"发起人：{sender_name} ({sender_id})\n"
            f"模式：{mode}\n\n"
            f"大家快上车呀！感兴趣的直接联系发起人！"
        )

        self._record_usage(sender_id)

        # 通过 chain_result 返回组件列表
        return event.chain_result([
            AtAll(), # 框架会自动根据平台将其转换为正确的“艾特全体”指令
            Plain(text_content)
        ])

    def _is_rate_limited(self, user_id: str) -> tuple[bool, str]:
        now = time.time()
        if user_id in self.cooldown:
            elapsed = now - self.cooldown[user_id]
            if elapsed < self.cooldown_seconds:
                return True, f"操作太快了，请等待 {int(self.cooldown_seconds - elapsed)} 秒。"
        today = time.strftime("%Y-%m-%d")
        if self.daily_count[user_id][today] >= self.daily_limit:
            return True, f"今天招募机会已用完。"
        return False, ""

    def _record_usage(self, user_id: str):
        self.cooldown[user_id] = time.time()
        self.daily_count[user_id][time.strftime("%Y-%m-%d")] += 1
