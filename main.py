import time
from collections import defaultdict
from astrbot.api.event import filter, AstrMessageEvent
from astrbot.api.star import Context, Star, register
from astrbot.api import logger

@register(
    "astrbot_plugin_naraka_recruit",
    "LK-von-Clausewitz",
    "永劫无间组队：修复 API 调用路径",
    "1.0.4",
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
        """检查消息中是否包含机器人昵称或是否被艾特"""
        msg_str = event.message_str
        if self.bot_nickname in msg_str:
            return True
        
        # 兼容性检查：如果 message_obj 有 at 信息
        try:
            for seg in event.message_obj.message:
                if seg.get("type") == "at":
                    # 只要有 at 节点就视为在叫机器人 (在大多数单机器人环境下适用)
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

        # 构造 OneBot 消息链
        message_chain = [
            {"type": "at", "data": {"qq": "all"}},
            {"type": "text", "data": {"text": f"\n🔥【永劫无间 {mode} 招募】🔥\n发起人：{sender_name} ({sender_id})\n模式：{mode}\n\n大家快上车呀！直接联系发起人即可！"}}
        ]

        # 核心修复点：调用 _send_group_message
        success = await self._send_group_message(event, message_chain)
        
        if success:
            self._record_usage(sender_id)
            return event.plain_result("✅ 小劫宝已帮你发布招募并@全体成员！")
        else:
            return event.plain_result("❌ 发布失败。请确保我是管理员，且群内@全体成员次数未达今日上限。")

    async def _send_group_message(self, event: AstrMessageEvent, message_chain: list) -> bool:
        """修复后的 API 调用方法"""
        try:
            # 获取群号
            group_id = getattr(event.message_obj, "group_id", None)
            if not group_id:
                logger.error("无法获取 group_id")
                return False

            request_data = {
                "action": "send_group_msg",
                "params": {
                    "group_id": group_id,
                    "message": message_chain
                }
            }

            # --- 关键修复：在 AstrBot v4 中，sapi 通常在 event.bot 下 ---
            bot = getattr(event, "bot", None) or getattr(event, "platform_instance", None)
            
            if bot and hasattr(bot, "sapi"):
                response = await bot.sapi.send_request(request_data)
                return response and response.get('status') == 'ok'
            
            logger.error("无法定位到 sapi 接口，请检查适配器连接。")
            return False
        except Exception as e:
            logger.error(f"API调用发生异常: {e}")
            return False

    def _is_rate_limited(self, user_id: str) -> tuple[bool, str]:
        now = time.time()
        if user_id in self.cooldown:
            elapsed = now - self.cooldown[user_id]
            if elapsed < self.cooldown_seconds:
                return True, f"操作太快了，请等待 {int(self.cooldown_seconds - elapsed)} 秒。"
        
        today = time.strftime("%Y-%m-%d")
        if self.daily_count[user_id][today] >= self.daily_limit:
            return True, f"今天 {self.daily_limit} 次招募机会已用完。"
        return False, ""

    def _record_usage(self, user_id: str):
        self.cooldown[user_id] = time.time()
        self.daily_count[user_id][time.strftime("%Y-%m-%d")] += 1

    async def terminate(self):
        logger.info("永劫无间招募插件已卸载。")
