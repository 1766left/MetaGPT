import asyncio
import platform
import fire

from metagpt.software_company import SoftwareCompany
from metagpt.actions import Action
from metagpt.roles import Role
from metagpt.schema import Message
from metagpt.logs import logger
from pydantic import BaseModel, Field
from metagpt.config import CONFIG
from metagpt.environment import Environment
from metagpt.utils.common import NoMoneyException

class ContinueStory(Action):
    """Action: 续写故事"""

    # PROMPT_TEMPLATE = """
    # ## 背景
    # 你是 {name}, 你和另几个人在玩故事接龙的游戏.
    # ## 你的特点
    # 你是一个 {character} 的人，你喜欢用 {tone} 的语气来讲故事。
    # ## 之前的故事
    # {context}
    # ## 你的任务
    # 接下来轮到你讲故事了，你需要在 {name} 的视角下，用 {tone} 的语气，继续讲故事，你的故事应该是："""

    PROMPT_TEMPLATE = """
    ## 背景
    你是 {name}, 你和{opponent_name}在玩故事接龙的游戏.
    ## 你的特点
    你是一个 {character} 的人，你喜欢用 {tone} 的语气来讲故事。
    ## 之前的故事
    {context}
    ## 你的任务
    接下来轮到你了，你需要在 {name} 的视角下继续讲故事。请发挥你 {character} 的特点，用不超过100字来描述接下来发生了什么，语气应该是 {tone} 的。你接龙的内容是："""

    def __init__(self, name="ContinueStory", context=None, llm=None):
        super().__init__(name, context, llm)

    async def run(self, context: str, name: str, opponent_name: str, character: str, tone: str):

        prompt = self.PROMPT_TEMPLATE.format(context=context, name=name, opponent_name=opponent_name, character=character, tone=tone)
        # logger.info(prompt)

        rsp = await self._aask(prompt)

        print(rsp)
        return rsp

class StoryTeller(Role):
    def __init__(
        self,
        name: str,
        profile: str,
        character: str,
        tone: str,
        next_teller: str,
        **kwargs,
    ):
        super().__init__(name, profile, **kwargs)
        self._init_actions([ContinueStory])
        self._watch([ContinueStory])
        self.name = name
        self.opponent_name = next_teller
        self.character = character
        self.tone = tone

    async def _observe(self) -> int:
        await super()._observe()
        # accept the very first human instruction (the debate topic) or messages sent (from opponent) to self,
        # disregard own messages from the last round
        self._rc.news = [msg for msg in self._rc.news if msg.send_to == self.name]
        return len(self._rc.news)

    async def _act(self) -> Message:
        logger.info(f"{self._setting}: ready to {self._rc.todo}")

        msg_history = self._rc.memory.get_by_actions([ContinueStory])
        context = []
        for m in msg_history:
            context.append(str(m))
        context = "\n".join(context)

        rsp = await ContinueStory().run(context=context, name=self.name, opponent_name=self.opponent_name, character=self.character, tone=self.tone)

        msg = Message(
            content=rsp,
            role=self.profile,
            cause_by=ContinueStory,
            sent_from=self.name,
            send_to=self.opponent_name,
        )

        return msg


class RoundTable(SoftwareCompany):    
    def start_story(self, idea, first):
        """Start a project from publishing boss requirement."""
        self.idea = idea
        self.environment.publish_message(
            Message(role="BOSS", content=idea, cause_by=ContinueStory, send_to=first))



async def startup(idea: str, investment: float = 3.0, n_round: int = 5,
                  code_review: bool = False, run_tests: bool = False):
    company = RoundTable()
    company.hire([
        StoryTeller("Jerry", "HappyBoy", "积极向上", "认真努力", "Tom"),
        StoryTeller("Tom", "SadBoy", "消极悲观", "忧郁低沉", "Bruce"),
        StoryTeller("Bruce", "FunnyBoy", "搞笑不正经", "轻松滑稽", "Jerry")
    ])
    company.invest(investment)
    company.start_story(idea, "Bruce")
    await company.run(n_round=n_round)


def main(idea: str = "去森林里冒险", investment: float = 3.0, n_round: int = 10):
    if platform.system() == "Windows":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(startup(idea, investment, n_round))


if __name__ == '__main__':
    fire.Fire(main)

    