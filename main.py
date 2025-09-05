from astrbot.api.event import filter, AstrMessageEvent, MessageEventResult
from astrbot.api.star import Context, Star, register
import astrbot.api.event.filter as filter
from astrbot.api import logger
import os
import json

@register("astrbot_plugin_mh", "MH集会码", "怪物猎人集会码登记插件", "1.0")
class MyPlugin(Star):
    def __init__(self, context: Context) -> None:
        super().__init__(context)
        self.PLUGIN_NAME = "astrbot_plugin_mh"
        PLUGIN_NAME = self.PLUGIN_NAME
        path = os.path.abspath(os.path.dirname(__file__))

        # 集会码数据文件路径
        self.gather_code_path = f"data/{PLUGIN_NAME}_gather_code.json"

        # 如果文件不存在则创建空文件
        if not os.path.exists(self.gather_code_path):
            with open(self.gather_code_path, "w", encoding="utf-8") as f:
                f.write(json.dumps({}, ensure_ascii=False, indent=2))
       # 读取文件内容
        with open(self.gather_code_path, "r", encoding="utf-8") as f:
            self.gather_code_data = json.loads(f.read())

    def save_gather_code_data(self):
        with open(self.gather_code_path, "w", encoding="utf-8") as f:
            f.write(json.dumps(self.gather_code_data, ensure_ascii=False, indent=2))

    @filter.command("i")
    async def register_code(self, event: AstrMessageEvent):
        """登记集会码，格式：/i 集会码 [备注]"""
        logger.info("触发集会码登记指令")
        group_id = event.get_group_id()
        user_id = event.get_sender_id()
        key = f"{group_id}_{user_id}"
        # 格式：/i 集会码 [备注]
        args = event.message_str.replace("i", "").strip().split(maxsplit=1)
        code = args[0] if args else ""
        desc = args[1] if len(args) > 1 else ""
        if not code:
            yield event.plain_result("请输入集会码，例如：/i 集会码 [备注]")
            return
        # 按群分组，每个群下是用户id和集会码信息
        if group_id not in self.gather_code_data:
            self.gather_code_data[group_id] = {}
        self.gather_code_data[group_id][user_id] = {
            "code": code,
            "desc": desc,
            "mark": f"MH-{user_id}"  # 标记，可自定义
        }
        self.save_gather_code_data()
        yield event.plain_result(
            f"已登记集会码：{code}\n备注：{desc}\n标记：MH-{user_id}"
        )

    @filter.command("f")
    async def query_codes(self, event: AstrMessageEvent):
        """查询当前群所有集会码，格式：/查码"""
        logger.info("触发集会码查询指令!")
        group_id = event.get_group_id()
        group_data = self.gather_code_data.get(group_id, {})
        if not group_data:
            yield event.plain_result("本群还没有登记任何集会码。")
            return
        result_lines = ["本群已登记的集会码："]
        for uid, info in group_data.items():
            code = info.get("code", "")
            desc = info.get("desc", "")
            mark = info.get("mark", "")
            result_lines.append(f"用户ID: {uid}\n集会码: {code}\n备注: {desc}\n")
            result_lines.append(f"--------------------\n")
        yield event.plain_result("\n".join(result_lines))
    
    @filter.command("d")
    async def delete_code(self, event: AstrMessageEvent):
        """删除自己的集会码，格式：/删码"""
        logger.info("触发集会码删除指令!")
        group_id = event.get_group_id()
        user_id = event.get_sender_id()
        group_data = self.gather_code_data.get(group_id, {})
        if user_id in group_data:
            del group_data[user_id]
            self.gather_code_data[group_id] = group_data
            self.save_gather_code_data()
            yield event.plain_result("你的集会码已删除。")
        else:
            yield event.plain_result("你没有登记过集会码。")
