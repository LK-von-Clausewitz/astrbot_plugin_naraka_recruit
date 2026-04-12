import time
import re
from collections import defaultdict
from astrbot.api.event import filter, AstrMessageEvent
from astrbot.api.star import Context, Star, register
from astrbot.api import logger@register(
    "astrbot_plugin_naraka_recruit",
    "YLK-von-Clausewitz",
    "永劫无间组队招募插件：@小劫宝 双排组队/三排组队/娱乐组队",
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
        
        self.mode_names = {
            "双排": "双排",
            "三排": "三排", 
            "娱乐": "娱乐"
        }
        
        logger.info("永劫无间招募插件已加载！")

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
            if response and isinstance(response, dict) and response.get('status') == 'ok':
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

    def _parse_message(self, message_str: str) -> str | None:
        patterns = [
            r'双排\s*组队',
            r'三排\s*组队',
            r'娱乐\s*组队'
        ]
        
        for pattern in patterns:
            if re.search(pattern, message_str):
                if '双排' in message_str:
                    return '双排'
                elif '三排' in message_str:
                    return '三排'
                elif '娱乐' in message_str:
                    return '娱乐'
        return None

    @filter.group_message()
    async def handle_group_message(self, event: AstrMessageEvent):
        try:
            message_obj = event.message_obj
            if not hasattr(message_obj, 'message') or not message_obj.message:
                return
            
            is_at_bot = False
            plain_text = ""
            
            message_list = message_obj.message
            if not isinstance(message_list, list):
                return
            
            for seg in message_list:
                if isinstance(seg, dict):
                    if seg.get('type') == 'at':
                        data = seg.get('data', {})
                        if isinstance(data, dict) and data.get('qq') == 'all':
                            continue
                        if isinstance(data, dict):
                            at_qq = data.get('qq')
                            if at_qq and str(at_qq) == str(event.platform.get_bot_id()):
                                is_at_bot = True
                    elif seg.get('type') == 'text':
                        data = seg.get('data', {})
                        if isinstance(data, dict):
                            plain_text += data.get('text', '')
            
            if not is_at_bot:
                return
            
            mode = self._parse_message(plain_text)
            if not mode:
                yield event.plain_result("💡 用法：@小劫宝 双排组队 或 @小劫宝 三排组队 或 @小劫宝 娱乐组队")
                return
            
            sender_id = event.get_sender_id()
            sender_name = event.get_sender_name()
            
            limited, msg = self._is_rate_limited(sender_id)
            if limited:
                yield event.plain_result(f"❌ {msg}")
                return
            
            at_all_segment = {
                "type": "at",
                "data": {"qq": "all"}
            }
            
            text_content = (
                f"【永劫无间 {self.mode_names[mode]} 招募】\n"
                f"🏮 发起人：{sender_name}（QQ: {sender_id}）\n"
                f"🎮 模式：{self.mode_names[mode]}\n"
                f"⏰ 时间：现在\n\n"
                f"快来一起聚窟洲征战！直接联系发起人即可！"
            )
            
            text_segment = {
                "type": "text",
                "data": {"text": text_content}
            }
            
            message_chain = [at_all_segment, text_segment]
            
            success = await self._send_group_message(event, message_chain)
            if success:
                self._record_usage(sender_id)
                yield event.plain_result(f"✅ 已发布{self.mode_names[mode]}招募信息并@全体成员！")
            else:
                yield event.plain_result("❌ 发布失败，请确保机器人是群管理员且@全体成员次数未达上限。")
                
        except Exception as e:
            logger.error(f"处理消息时出错: {e}")
            yield event.plain_result("❌ 插件处理出错，请查看日志。")

    async def terminate(self):
        logger.info("永劫无间招募插件已卸载。")
```

```yaml
# metadata.yaml
name: astrbot_plugin_naraka_recruit
desc: 永劫无间组队招募插件：@小劫宝 双排组队/三排组队/娱乐组队
version: 1.0.0
author: YourName
repo: https://github.com/YourGitHubUsername/astrbot_plugin_naraka_recruit
```

```json
// _conf_schema.json
{
  "type": "object",
  "properties": {
    "cooldown_seconds": {
      "type": "integer",
      "title": "冷却时间(秒)",
      "default": 30,
      "description": "同一用户两次招募的最小间隔"
    },
    "daily_limit": {
      "type": "integer",
      "title": "每日限制次数",
      "default": 3,
      "description": "每个用户每天最大招募次数"
    }
  }
}
