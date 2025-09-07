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
        # 管理员QQ号数据文件路径
        self.admins_path = f"data/{PLUGIN_NAME}_admins.json"

        # 如果文件不存在则创建空文件
        if not os.path.exists(self.gather_code_path):
            with open(self.gather_code_path, "w", encoding="utf-8") as f:
                f.write(json.dumps({}, ensure_ascii=False, indent=2))
        if not os.path.exists(self.admins_path):
            with open(self.admins_path, "w", encoding="utf-8") as f:
                f.write(json.dumps({}, ensure_ascii=False, indent=2))
        
       # 读取文件内容
        with open(self.gather_code_path, "r", encoding="utf-8") as f:
            self.gather_code_data = json.loads(f.read())
        with open(self.admins_path, "r", encoding="utf-8") as f:
            self.admins_data = json.loads(f.read())

    def save_gather_code_data(self):
        with open(self.gather_code_path, "w", encoding="utf-8") as f:
            f.write(json.dumps(self.gather_code_data, ensure_ascii=False, indent=2))

    def save_admins_data(self):
        with open(self.admins_path, "w", encoding="utf-8") as f:
            f.write(json.dumps(self.admins_data, ensure_ascii=False, indent=2))

    # 判断QQ号是否在管理员列表中
    def is_admin_qq(self, group_id, qq):
        """判断该QQ号是否在本群的管理员列表中"""
        return group_id in self.admins_data and str(qq) in [str(x) for x in self.admins_data[group_id]]

    # 登记集会码，格式：/i 集会码 [备注]
    @filter.command("i")
    async def register_code(self, event: AstrMessageEvent):
        """登记集会码 格式：/i 集会码 [备注]"""
        logger.info("触发集会码登记指令")
        group_id = event.get_group_id()
        user_id = event.get_sender_id()
        user_name = event.message_obj.sender.nickname
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
        self.gather_code_data[group_id][str(user_id)] = {
            "code": code,
            "desc": desc,
            "mark": f"MH-{user_name}",  # 标记，可自定义
            "nick": f"{user_name}",  # 记录QQ昵称，方便管理员删除
            "qq": str(user_id)  # 新增QQ字段
        }
        self.save_gather_code_data()
        yield event.plain_result(
            f"已登记集会码：{code}\n备注：{desc}\n标记：MH-{user_name}"
        )

    # 查询集会码，格式：/f
    @filter.command("f")
    async def query_codes(self, event: AstrMessageEvent):
        """查询当前群所有集会码 格式：/f"""
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
            result_lines.append(f"--------------------")
            result_lines.append(f"用户ID: {uid}\n集会码: {code}\n备注: {desc}")
        yield event.plain_result("\n".join(result_lines))
    
    # 删除自己的集会码，格式：/d
    @filter.command("d")
    async def delete_code(self, event: AstrMessageEvent):
        """删除自己的集会码 格式：/d"""
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

    # 添加有权限的QQ号，格式：/addadmin QQ号
    @filter.command("addadmin")
    async def add_admin(self, event: AstrMessageEvent):
        """添加有权限的QQ号，仅astrbot管理员可使用 格式：/addadmin QQ号"""
        group_id = event.get_group_id()
        if not event.is_admin():
            yield event.plain_result("无权限使用。")
            return
        args = event.message_str.replace("addadmin", "").strip().split()
        if not args:
            yield event.plain_result("请输入要添加的QQ号，例如：/addadmin 123456789")
            return
        qq = args[0]
        if group_id not in self.admins_data:
            self.admins_data[group_id] = []
        if qq in self.admins_data[group_id]:
            yield event.plain_result(f"QQ号 {qq} 已有集会码清除权限。")
            return
        self.admins_data[group_id].append(qq)
        self.save_admins_data()
        yield event.plain_result(f"已添加QQ号 {qq} 集会码清除权限。")

    # 删除有权限的QQ号，格式：/deladmin QQ号
    @filter.command("deladmin")
    async def del_admin(self, event: AstrMessageEvent):
        """删除有权限的QQ号，仅astrbot管理员可使用 格式：/deladmin QQ号"""
        group_id = event.get_group_id()
        if not event.is_admin():
            yield event.plain_result("无权限使用。")
            return
        args = event.message_str.replace("deladmin", "").strip().split()
        if not args:
            yield event.plain_result("请输入要删除的QQ号，例如：/deladmin 123456789")
            return
        qq = args[0]
        if group_id not in self.admins_data or qq not in self.admins_data[group_id]:
            yield event.plain_result(f"QQ号 {qq} 不在本群权限列表中。")
            return
        self.admins_data[group_id].remove(qq)
        self.save_admins_data()
        yield event.plain_result(f"已移除QQ号 {qq} 的集会码清除权限。")

    # 清空本群所有集会码，格式：/clear
    @filter.command("clear")
    async def clear_codes(self, event: AstrMessageEvent):
        """清空本群所有集会码，仅限群主/管理员 格式：/clear"""
        logger.info("触发集会码清空指令!")
        group_id = event.get_group_id()
        admin = self.is_admin_qq(group_id, event.get_sender_id) or event.is_admin()
        if not admin:
            yield event.plain_result("无权限使用。")
            return
        if group_id in self.gather_code_data:
            self.gather_code_data[group_id] = {}
            self.save_gather_code_data()
            yield event.plain_result("本群所有集会码已清空。")
        else:
            yield event.plain_result("本群没有登记过集会码。")

    # 删除指定QQ号或昵称的集会码，格式：/deluser QQ号 或 /deluser 昵称
    @filter.command("deluser")
    async def delete_user_code(self, event: AstrMessageEvent):
        """删除指定QQ号或昵称的集会码，仅限管理员 格式：/deluser QQ号 或 /deluser 昵称"""
        group_id = event.get_group_id()
        user_qq = event.get_sender_id()
        user_name = event.message_obj.sender.nickname
        if not self.is_admin_qq(group_id, user_qq):
            yield event.plain_result("无权限使用。")
            return
        args = event.message_str.replace("deluser", "").strip().split()
        if not args:
            yield event.plain_result("请输入要删除的QQ号或昵称，例如：/deluser 123456789 或 /deluser 昵称")
            return
        target = args[0]
        group_data = self.gather_code_data.get(group_id, {})
        found = False
        for uid in list(group_data.keys()):
            info = group_data[uid]
            if uid == target or info.get("qq") == target or info.get("nick") == target:
                del group_data[uid]
                found = True
        if found:
            self.gather_code_data[group_id] = group_data
            self.save_gather_code_data()
            yield event.plain_result(f"已删除 {target} 的集会码。")
        else:
            yield event.plain_result(f"未找到 {target} 的集会码。")