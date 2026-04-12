import time
from collections import defaultdict
from astrbot.api.event import filter, AstrMessageEvent
from astrbot.api.star import Context, Star, register
from astrbot.api import logger

@register(
    "astrbot_plugin_naraka_recruit",
    "LK-von-Clausewitz",
    "永劫无间组队：CQ码稳定版",
    "1.0.6",
    "https://github.com/LK-von-Clausewitz/astrbot_plugin_naraka_recruit"
)
class NarakaRecruitPlugin(Star):
    def __init__(self, context: Context):
        super().__init__(context)
        self.cooldown = {}
        self.daily_count = defaultdict(lambda: defaultdict(int))
        self.cooldown_seconds = 30 # 两次招募之间的冷却时间
        self.daily_limit = 3       # 每个用户每天限额
        self.bot_nickname = "小劫宝"

    # --- 匹配逻辑 ---

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
        """检查消息中是否包含机器人昵称或是否被艾特"""
        msg_str = event.message_str
        if self.bot_nickname in msg_str:
            return True
        
        # 遍历消息链，检查是否有 at 类型节点
        try:
            message_chain = event.message_obj.message
            for seg in message_chain:
                if seg.get("type") == "at":
                    return True
        except:
            pass
        return False

    async def _handle_recruit(self, event: AstrMessageEvent, mode: str):
        sender_id = event.get_sender_id()
        sender_name = event.get_sender_name()

        # 1. 频率限制检查
        limited, msg = self._is_rate_limited(sender_id)
        if limited:
            return event.plain_result(f"❌ {msg}")

        # 2. 构造消息内容
        # 使用 [CQ:at,qq=all] 强制触发艾特全体
        # 后面紧跟内容，确保逻辑简单直接
        text_content = (
            f"[CQ:at,qq=all]\n"
            f"🔥【永劫无间 {mode} 招募】🔥\n"
            f"发起人：{sender_name} ({sender_id})\n"
            f"模式：{mode}\n"
            f"状态：等待队友中...\n\n"
            f"大家快上车呀！感兴趣的直接联系发起人！"
        )

        # 3. 记录使用次数
        self._record_usage(sender_id)

        # 4. 直接返回 plain_result 即可，框架会自动把 CQ 码传给底层
        return event.plain_result(text_content)

    # --- 辅助方法 ---

    def _is_rate_limited(self, user_id: str) -> tuple[bool, str]:
        now = time.time()
        # 冷却时间检查
        if user_id in self.cooldown:
            elapsed = now - self.cooldown[user_id]
            if elapsed < self.cooldown_seconds:
                wait = int(self.cooldown_seconds - elapsed)
                return True, f"操作太快了，请等待 {wait} 秒后再试。"
        
        # 每日次数限制
        today = time.strftime("%Y-%m-%d")
        if self.daily_count[user_id][today] >= self.daily_limit:
            return True, f"您今天 {self.daily_limit} 次招募机会已用完，明天再来吧。"
        
        return False, ""

    def _record_usage(self, user_id: str):
        self.cooldown[user_id] = time.time()
        today = time.strftime("%Y-%m-%d")
        self.daily_count[user_id][today] += 1

    async def terminate(self):
        logger.info("永劫无间招募插件已安全卸载。")
