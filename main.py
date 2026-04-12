import time
from collections import defaultdict
from astrbot.api.event import filter, AstrMessageEvent
from astrbot.api.star import Context, Star, register
from astrbot.api import logger

@register(
    "astrbot_plugin_naraka_recruit",
    "LK-von-Clausewitz",
    "永劫无间组队：通过检查文本中的机器人昵称触发",
    "1.0.3",
    "https://github.com/LK-von-Clausewitz/astrbot_plugin_naraka_recruit"
)
class NarakaRecruitPlugin(Star):
    def __init__(self, context: Context):
        super().__init__(context)
        self.cooldown = {}
        self.daily_count = defaultdict(lambda: defaultdict(int))
        self.cooldown_seconds = 30
        self.daily_limit = 3
        # 机器人的昵称，用于手动判断
        self.bot_nickname = "小劫宝"

    # --- 核心逻辑：不再使用 @filter.at_me ---

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
        """手动检查是否艾特了机器人或者提到了机器人名字"""
        msg_str = event.message_str
        # 1. 检查文字里是否有名字
        if self.bot_nickname in msg_str:
            return True
        
        # 2. 检查消息链里是否有 AT 节点 (兼容 Aiocqhttp 结构)
        try:
            # 获取当前机器人的 QQ 号
            self_id = str(getattr(event.platform, "self_id", ""))
            message_chain = event.message_obj.message
            for seg in message_chain:
                if seg.get("type") == "at":
                    if str(seg.get("data", {}).get("qq")) == self_id:
                        return True
        except:
            pass
            
        return False

    async def _handle_recruit(self, event: AstrMessageEvent, mode: str):
        sender_id = event.get_sender_id()
        sender_name = event.get_sender_name()

        # 频率限制检查
        limited, msg = self._is_rate_limited(sender_id)
        if limited:
            return event.plain_result(f"❌ {msg}")

        # 构建发送的消息链
        at_all_segment = {
            "type": "at",
            "data": {"qq": "all"}
        }
        text_content = (
            f"\n🔥【永劫无间 {mode} 招募】🔥\n"
            f"发起人：{sender_name} ({sender_id})\n"
            f"模式：{mode}\n\n"
            f"感兴趣的朋友请直接联系发起人！速速上车！"
        )
        text_segment = {
            "type": "text",
            "data": {"text": text_content}
        }
        message_chain = [at_all_segment, text_segment]

        # 调用发送
        success = await self._send_group_message(event, message_chain)
        if success:
            self._record_usage(sender_id)
            return event.plain_result("✅ 招募已发布并@全体成员！")
        else:
            return event.plain_result("❌ 发布失败，请检查管理权限或@全体次数。")

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
            return response and response.get('status') == 'ok'
        except Exception as e:
            logger.error(f"API调用异常: {e}")
            return False

    def _is_rate_limited(self, user_id: str) -> tuple[bool, str]:
        now = time.time()
        if user_id in self.cooldown:
            elapsed = now - self.cooldown[user_id]
            if elapsed < self.cooldown_seconds:
                return True, f"太快了，请等待 {int(self.cooldown_seconds - elapsed)} 秒。"
        
        today = time.strftime("%Y-%m-%d")
        if self.daily_count[user_id][today] >= self.daily_limit:
            return True, f"今天 {self.daily_limit} 次机会已用完。"
        return False, ""

    def _record_usage(self, user_id: str):
        self.cooldown[user_id] = time.time()
        self.daily_count[user_id][time.strftime("%Y-%m-%d")] += 1

    async def terminate(self):
        logger.info("永劫无间招募插件已卸载。")
