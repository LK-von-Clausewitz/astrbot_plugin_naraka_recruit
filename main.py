import time
from collections import defaultdict
from astrbot.api.event import filter, AstrMessageEvent
from astrbot.api.star import Context, Star, register
from astrbot.api import logger

@register(
    "astrbot_plugin_naraka_recruit",
    "YourName",
    "永劫无间招募插件：限定双排/三排/娱乐模式，普通成员可请求机器人@全体成员",
    "1.0.0",
    "https://github.com/YourGitHubUsername/astrbot_plugin_naraka_recruit"
)
class NarakaRecruitPlugin(Star):
    def __init__(self, context: Context):
        super().__init__(context)
        self.cooldown = {}
        self.daily_count = defaultdict(lambda: defaultdict(int))
        self.cooldown_seconds = 30
        self.daily_limit = 3
        
        self.valid_modes = {
            "双排": "👥",
            "三排": "👥👥", 
            "娱乐": "🎮"
        }

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

    @filter.command("recruit")
    async def recruit(self, event: AstrMessageEvent):
        """
        发布永劫无间招募
        用法：/recruit <模式> <备注>
        模式：双排/三排/娱乐
        """
        sender_id = event.get_sender_id()
        sender_name = event.get_sender_name()

        limited, msg = self._is_rate_limited(sender_id)
        if limited:
            yield event.plain_result(f"❌ {msg}")
            return

        raw_text = event.message_str.strip()
        args = raw_text[8:].strip().split(maxsplit=1)
        
        if not args:
            yield event.plain_result("❌ 用法：/recruit <模式> <备注>\n模式支持：双排、三排、娱乐\n例如：/recruit 三排 修罗局速来")
            return
            
        mode = args[0]
        if mode not in self.valid_modes:
            yield event.plain_result(f"❌ 模式「{mode}」无效！请选择：双排、三排、娱乐")
            return
            
        remark = args[1] if len(args) > 1 else "快来一起玩！"

        at_all_segment = {"type": "at", "data": {"qq": "all"}}
        mode_emoji = self.valid_modes[mode]
        text_content = (
            f"⚔️ 【永劫无间招募】 ⚔️\n"
            f"━━━━━━━━━━━━━━━━\n"
            f"🎮 模式：{mode_emoji} {mode}\n"
            f"👤 发起人：{sender_name}（{sender_id}）\n"
            f"📝 备注：{remark}\n"
            f"━━━━━━━━━━━━━━━━\n"
            f"感兴趣的兄弟直接联系发起人！"
        )
        text_segment = {"type": "text", "data": {"text": text_content}}
        message_chain = [at_all_segment, text_segment]

        success = await self._send_group_message(event, message_chain)
        if success:
            self._record_usage(sender_id)
            yield event.plain_result("✅ 永劫无间招募已发布！")
        else:
            yield event.plain_result("❌ 发布失败，请确保机器人是群管理员且@全体成员次数未达上限。")

    @filter.command("recruithelp")
    async def recruit_help(self, event: AstrMessageEvent):
        """显示帮助信息"""
        help_text = (
            "⚔️ 永劫无间招募插件帮助 ⚔️\n"
            "━━━━━━━━━━━━━━━━\n"
            "🎮 命令：/recruit <模式> <备注>\n"
            "📋 可用模式：\n"
            "   👥 双排 - 双人排位\n"
            "   👥👥 三排 - 三人排位\n" 
            "   🎮 娱乐 - 娱乐模式\n"
            "━━━━━━━━━━━━━━━━\n"
            "💡 示例：/recruit 三排 来会玩的"
        )
        yield event.plain_result(help_text)

    async def terminate(self):
        logger.info("永劫无间招募插件已卸载。")
