import time
from collections import defaultdict
from astrbot.api.event import filter, AstrMessageEvent
from astrbot.api.star import Context, Star, register
from astrbot.api import logger

@register(
    "astrbot_plugin_naraka_recruit",
    "LK-von-Clausewitz",
    "永劫无间组队插件：@机器人 + 关键词发布招募",
    "1.0.1",
    "https://github.com/LK-von-Clausewitz/astrbot_plugin_naraka_recruit"
)
class NarakaRecruitPlugin(Star):
    def __init__(self, context: Context):
        super().__init__(context)
        self.cooldown = {}
        self.daily_count = defaultdict(lambda: defaultdict(int))
        self.cooldown_seconds = 30
        self.daily_limit = 3

    # 修改正则：去掉 ^ 和 $，只要消息里包含关键词且艾特了机器人即可触发
    @filter.regex(r"双排组队")
    async def recruit_double(self, event: AstrMessageEvent):
        return await self._handle_recruit(event, "双排")

    @filter.regex(r"三排组队")
    async def recruit_triple(self, event: AstrMessageEvent):
        return await self._handle_recruit(event, "三排")

    @filter.regex(r"娱乐组队")
    async def recruit_casual(self, event: AstrMessageEvent):
        return await self._handle_recruit(event, "娱乐")

    async def _handle_recruit(self, event: AstrMessageEvent, mode: str):
        # 只有在艾特机器人的时候才触发，或者你可以根据需要去掉这个判断
        if not event.is_at_me:
            return

        sender_id = event.get_sender_id()
        sender_name = event.get_sender_name()

        # 频率检查
        limited, msg = self._is_rate_limited(sender_id)
        if limited:
            return event.plain_result(f"❌ {msg}")

        # 构建消息链
        # 注意：@全体成员 在不同平台协议下可能不同，这里使用标准的 onebot 风格
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

        # 调用发送逻辑
        success = await self._send_group_message(event, message_chain)
        if success:
            self._record_usage(sender_id)
            return event.plain_result("✅ 已帮你发布招募并@全体成员！")
        else:
            return event.plain_result("❌ 发布失败，请确保机器人是管理员且有@全体权限。")

    # 辅助方法保持不变...
    async def _send_group_message(self, event: AstrMessageEvent, message_chain: list) -> bool:
        try:
            request_data = {
                "action": "send_group_msg",
                "params": {
                    "group_id": event.message_obj.group_id,
                    "message": message_chain
                }
            }
            # 确保 sapi 可用
            response = await event.platform.sapi.send_request(request_data)
            return response and response.get('status') == 'ok'
        except Exception as e:
            logger.error(f"发送异常: {e}")
            return False

    def _is_rate_limited(self, user_id: str) -> tuple[bool, str]:
        now = time.time()
        if user_id in self.cooldown:
            elapsed = now - self.cooldown[user_id]
            if elapsed < self.cooldown_seconds:
                return True, f"操作频繁，请等 {int(self.cooldown_seconds - elapsed)} 秒。"
        today = time.strftime("%Y-%m-%d")
        if self.daily_count[user_id][today] >= self.daily_limit:
            return True, "今天招募次数已用完。"
        return False, ""

    def _record_usage(self, user_id: str):
        self.cooldown[user_id] = time.time()
        self.daily_count[user_id][today := time.strftime("%Y-%m-%d")] += 1
