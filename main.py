import time
from collections import defaultdict
from astrbot.api.event import filter, AstrMessageEvent
from astrbot.api.star import Context, Star, register
from astrbot.api import logger

@register(
    "astrbot_plugin_naraka_recruit",
    "LK-von-Clausewitz",
    "永劫无间组队插件：@机器人 + 关键词发布招募",
    "1.0.2",
    "https://github.com/LK-von-Clausewitz/astrbot_plugin_naraka_recruit"
)
class NarakaRecruitPlugin(Star):
    def __init__(self, context: Context):
        super().__init__(context)
        self.cooldown = {}
        self.daily_count = defaultdict(lambda: defaultdict(int))
        self.cooldown_seconds = 30
        self.daily_limit = 3

    # --- 核心逻辑：使用 @filter.at_me() 确保只有艾特机器人时才响应 ---

    @filter.at_me()
    @filter.regex(r"双排组队")
    async def recruit_double(self, event: AstrMessageEvent):
        return await self._handle_recruit(event, "双排")

    @filter.at_me()
    @filter.regex(r"三排组队")
    async def recruit_triple(self, event: AstrMessageEvent):
        return await self._handle_recruit(event, "三排")

    @filter.at_me()
    @filter.regex(r"娱乐组队")
    async def recruit_casual(self, event: AstrMessageEvent):
        return await self._handle_recruit(event, "娱乐")

    async def _handle_recruit(self, event: AstrMessageEvent, mode: str):
        sender_id = event.get_sender_id()
        sender_name = event.get_sender_name()

        # 1. 频率限制检查
        limited, msg = self._is_rate_limited(sender_id)
        if limited:
            return event.plain_result(f"❌ {msg}")

        # 2. 构建消息链 (OneBot 格式)
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

        # 3. 发送群消息
        success = await self._send_group_message(event, message_chain)
        
        if success:
            self._record_usage(sender_id)
            return event.plain_result("✅ 小劫宝已帮你发布招募并@全体成员！")
        else:
            # 如果失败，通常是因为没有管理员权限或 @全体成员 次数用完
            return event.plain_result("❌ 发布失败，请确保机器人是管理员且有发送艾特全体的权限。")

    async def _send_group_message(self, event: AstrMessageEvent, message_chain: list) -> bool:
        """调用底层 API 发送群消息"""
        try:
            request_data = {
                "action": "send_group_msg",
                "params": {
                    "group_id": event.message_obj.group_id,
                    "message": message_chain
                }
            }
            # 通过 sapi 发送请求
            response = await event.platform.sapi.send_request(request_data)
            if response and response.get('status') == 'ok':
                return True
            logger.error(f"发送群消息失败: {response}")
            return False
        except Exception as e:
            logger.error(f"调用发送消息API时发生异常: {e}")
            return False

    def _is_rate_limited(self, user_id: str) -> tuple[bool, str]:
        """检查用户是否触发冷却或每日上限"""
        now = time.time()
        # 冷却检查
        if user_id in self.cooldown:
            elapsed = now - self.cooldown[user_id]
            if elapsed < self.cooldown_seconds:
                wait = int(self.cooldown_seconds - elapsed)
                return True, f"操作过于频繁，请等待 {wait} 秒后再试。"
        
        # 每日上限检查
        today = time.strftime("%Y-%m-%d")
        if self.daily_count[user_id][today] >= self.daily_limit:
            return True, f"您今天已经使用了 {self.daily_limit} 次招募机会，请明天再来。"
        
        return False, ""

    def _record_usage(self, user_id: str):
        """记录用户使用时间和次数"""
        self.cooldown[user_id] = time.time()
        today = time.strftime("%Y-%m-%d")
        self.daily_count[user_id][today] += 1

    async def terminate(self):
        logger.info("永劫无间招募插件已安全卸载。")
