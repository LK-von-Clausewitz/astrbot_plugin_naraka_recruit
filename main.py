from collections import defaultdict
from astrbot.api.event import filter, AstrMessageEvent
from astrbot.api.star import Context, Star, register
from astrbot.api import logger
@register(
    "astrbot_plugin_naraka_recruit",
    "LK-von-Clausewitz",
    "永劫无间专属招募插件：@小劫宝 双排组队/三排组队/娱乐组队",
    "1.0.0",
    "https://github.com/LK-von-Clausewitz/astrbot_plugin_naraka_recruit"
)
class NarakaRecruitPlugin(Star):
    def __init__(self, context: Context):
        super().__init__(context)
        # 冷却记录：{user_id: last_use_timestamp}
        self.cooldown = {}
        # 每日次数记录：{user_id: date_str -> count}
        self.daily_count = defaultdict(lambda: defaultdict(int))
        # 限制参数
        self.cooldown_seconds = 30          # 冷却时间（秒）
        self.daily_limit = 3                # 每人每天最大次数
        # 机器人名称
        self.bot_names = ["小劫宝"]

    async def _send_group_message(self, event: AstrMessageEvent, message_chain: list) -> bool:
        """通过 OneBot API 发送群消息（支持@全体成员）"""
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
        """检查是否触发限制，返回 (是否被限制, 提示信息)"""
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
        """记录一次使用"""
        self.cooldown[user_id] = time.time()
        today = time.strftime("%Y-%m-%d")
        self.daily_count[user_id][today] += 1

    @filter.command("双排组队")
    async def recruit_double(self, event: AstrMessageEvent):
        """双排组队招募"""
        await self._handle_recruit(event, "双排")

    @filter.command("三排组队")
    async def recruit_triple(self, event: AstrMessageEvent):
        """三排组队招募"""
        await self._handle_recruit(event, "三排")

    @filter.command("娱乐组队")
    async def recruit_fun(self, event: AstrMessageEvent):
        """娱乐组队招募"""
        await self._handle_recruit(event, "娱乐")

    async def _handle_recruit(self, event: AstrMessageEvent, mode: str):
        """处理招募逻辑"""
        sender_id = event.get_sender_id()
        sender_name = event.get_sender_name()

        # 检查是否被限制
        limited, msg = self._is_rate_limited(sender_id)
        if limited:
            yield event.plain_result(f"❌ {msg}")
            return

        # 构造 @全体成员 消息段（OneBot 11 标准）
        at_all_segment = {
            "type": "at",
            "data": {"qq": "all"}
        }
        
        mode_emoji = {
            "双排": "👥",
            "三排": "👥👤", 
            "娱乐": "🎮"
        }
        
        text_content = (
            f"【永劫无间 {mode}招募】{mode_emoji.get(mode, '')}\n"
            f"━━━━━━━━━━━━━━━━\n"
            f"发起人：{sender_name}\n"
            f"模式：{mode}\n"
            f"状态：等待队友中...\n"
            f"━━━━━━━━━━━━━━━━\n"
            f"感兴趣的朋友请直接联系发起人！"
        )
        
        text_segment = {
            "type": "text",
            "data": {"text": text_content}
        }
        message_chain = [at_all_segment, text_segment]

        success = await self._send_group_message(event, message_chain)
        if success:
            self._record_usage(sender_id)
            yield event.plain_result(f"✅ {mode}招募信息已发布并@全体成员，祝你找到好队友！")
        else:
            yield event.plain_result("❌ 发布失败，请确保机器人是群管理员且@全体成员次数未达上限。")

    async def terminate(self):
        """插件卸载时的清理工作"""
        logger.info("永劫无间招募插件已卸载。")
