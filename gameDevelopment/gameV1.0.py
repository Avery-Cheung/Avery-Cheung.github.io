# interactive_demo.py
import random
import threading
import time
import sys

# ====== 配置 ======
INTERACTIVE_DICE = True  # 开关：是否启用终端闪现交互式骰子
DEFAULT_DICE_SPEED = 0.12  # 默认闪现间隔（秒），数值越小变化越快

# ====== 基础系统 ======
class Dice:
    @staticmethod
    def roll(sides, times=1):
        if sides < 1 or times < 1:
            raise ValueError("骰子参数错误：必须 sides>=1, times>=1")
        return [random.randint(1, sides) for _ in range(times)]

def interactive_roll(sides: int, player, hint: str = None):
    """
    在终端闪现 1..sides 的数字，按回车停止并返回当前数字。
    player.dice_speed 控制闪现速度（秒）。
    如果环境不支持交互（或 INTERACTIVE_DICE=False），会回退到随机一次 roll。
    """
    if not INTERACTIVE_DICE or not sys.stdin or not sys.stdin.isatty():
        # 非交互环境或显式关闭，直接返回随机结果
        return random.randint(1, sides)

    stop_event = threading.Event()
    result = [random.randint(1, sides)]

    def flicker():
        speed = max(0.01, getattr(player, "dice_speed", DEFAULT_DICE_SPEED))
        # 持续闪现，允许运行过程中 player.dice_speed 被修改（动态生效）
        while not stop_event.is_set():
            # 每一轮用当前 speed
            speed = max(0.01, getattr(player, "dice_speed", DEFAULT_DICE_SPEED))
            n = random.randint(1, sides)
            result[0] = n
            # \r 覆盖当前行，末尾留空格以覆盖旧字符
            sys.stdout.write(f"\r骰子 [{sides}] 闪现: {n}   ")
            sys.stdout.flush()
            time.sleep(speed)
        # 清理行尾
        sys.stdout.write("\r")
        sys.stdout.flush()

    thread = threading.Thread(target=flicker, daemon=True)
    thread.start()

    prompt = "(按回车停止闪现)"
    if hint:
        prompt = f"{hint} {prompt}"
    try:
        input(prompt)  # 等待回车
    except KeyboardInterrupt:
        # 如果用 Ctrl-C，中断也停止闪现并返回当前结果
        pass
    stop_event.set()
    thread.join(timeout=1.0)
    roll = result[0]
    print(f"\n最终判定 → {roll}")
    return roll

# ====== Card / Player / Deck 系统 ======
class Card:
    def __init__(self, name, description, dice_sides=None, outcomes=None, stable_effect=None):
        """
        outcomes 支持两种格式：
        - { (min,max): effect_callable }    单层判定
        - { (min,max): nested_outcomes_dict }  嵌套判定（进入下一层会重新掷骰）
        effect_callable(user, target, roll) -> str 描述
        stable_effect(user, target) -> str
        """
        self.name = name
        self.description = description
        self.dice_sides = dice_sides
        self.outcomes = outcomes or {}
        self.stable_effect = stable_effect

    def play(self, user, target):
        if self.dice_sides:
            return self._resolve_outcome(user, target, self.outcomes, self.dice_sides)
        elif self.stable_effect:
            return self.stable_effect(user, target)
        return f"{self.name} 没有定义效果"

    def _resolve_outcome(self, user, target, outcomes, dice_sides):
        # 交互式掷骰：使用 player's dice_speed（若启用）
        roll = None
        try:
            roll = interactive_roll(dice_sides, user, hint=f"正在掷 {self.name}（范围 1-{dice_sides}）")
        except Exception:
            # 任何交互错误都回退到随机
            roll = random.randint(1, dice_sides)

        # 找出对应区间
        for rng, effect in outcomes.items():
            if rng[0] <= roll <= rng[1]:
                if callable(effect):
                    return effect(user, target, roll)
                elif isinstance(effect, dict):
                    # 嵌套判定：再次掷骰（可能同样交互）
                    return self._resolve_outcome(user, target, effect, dice_sides)
                else:
                    return f"{self.name} 无效效果定义"
        return f"{self.name} 骰到 {roll} → 没有匹配的结果（健壮处理）"


class Player:
    def __init__(self, name, deck):
        self.name = name
        self.hp = 10
        self.san = 10
        self.deck = deck[:]  # 模板复制
        random.shuffle(self.deck)
        self.hand = []
        self.discard = []
        # 每个玩家有自己的闪现速度（可被卡牌修改）
        self.dice_speed = DEFAULT_DICE_SPEED

    @property
    def actions(self):
        return max(2, self.hp // 2)

    def draw(self, n=1):
        for _ in range(n):
            if not self.deck:
                self.shuffle_discard_into_deck()
            if self.deck:
                self.hand.append(self.deck.pop(0))

    def shuffle_discard_into_deck(self):
        if not self.discard:
            return
        self.deck = self.discard[:]
        self.discard.clear()
        random.shuffle(self.deck)

    def play_card(self, index, target):
        if 0 <= index < len(self.hand):
            card = self.hand.pop(index)
            self.discard.append(card)
            return card.play(self, target)
        return "无效操作"

    def is_dead(self):
        return self.hp <= 0 or self.san <= 0

    def status(self):
        return f"{self.name} 状态 → HP:{self.hp} SAN:{self.san} 行动力:{self.actions} 手牌:{[c.name for c in self.hand]} (闪现速:{self.dice_speed:.3f}s)"

# ====== 卡牌效果范例（包含可修改 dice_speed 的卡） ======
def normal_attack(user, target):
    target.hp -= 1
    # HP 减少不会自动扣 SAN（你的规则是扣HP会跟着扣SAN的，如果需要，请把下面一行取消注释）
    # user.san -= 1  # 若需：扣1HP同时扣1SAN（你之前有这个规则）
    return f"{user.name} 普通攻击 → {target.name} -1 HP"

def blood_attack(user, target, roll):
    # 这里的 roll 是最后闪现停止的数字，判定成功/失败根据区间
    if 1 <= roll <= 4:  # 4/6 成功
        target.hp -= 3
        user.san -= 1
        return f"{user.name} 血祭猛攻 成功（{roll}）→ {target.name} -3 HP，自身 -1 SAN"
    else:
        user.san -= 2
        return f"{user.name} 血祭猛攻 失败（{roll}）→ 自身 -2 SAN"

def strawman(user, target, roll):
    if roll == 1:
        # 标记敌人的下一张牌“无效” —— 这里以简化文本演示（真实机制需额外跟踪状态）
        # 我们返回一段描述，后续可以扩展为在 Player 上设置一个状态字段来实际生效
        target._next_card_invalid = True
        return f"{user.name} 稻草人（{roll}）→ 标记 {target.name} 下一张牌为无效"
    else:
        # 放大：示意文本；实际放大会在判定时检测状态来实现
        target._next_card_amplified = True
        return f"{user.name} 稻草人（{roll}）→ 放大 {target.name} 下一张牌效果（演示）"

def weekend(user, target, roll):
    if roll in [6, 7]:
        target._skip_next_turn = True
        return f"{user.name} 周末偷懒（{roll}）→ {target.name} 跳过下回合"
    else:
        return f"{user.name} 周末偷懒（{roll}）→ 什么都没发生"

# 控制闪现速度的示例卡
def slow_down(user, target):
    user.dice_speed *= 1.6  # 变慢 60%
    return f"{user.name} 使用 慢速药 → 本人掷骰闪现变慢（{user.dice_speed:.3f}s）"

def speed_up(user, target):
    user.dice_speed = max(0.02, user.dice_speed * 0.5)  # 加速（向下限靠拢）
    return f"{user.name} 使用 加速药 → 本人掷骰闪现变快（{user.dice_speed:.3f}s）"

# ====== 牌库模板（包含示例速度卡） ======
deck_template = [
    Card("普通攻击", "造成 1 HP", stable_effect=normal_attack),
    Card("血祭猛攻", "高伤害但有风险", dice_sides=6, outcomes={(1,6): blood_attack}),
    Card("稻草人谬误", "概率干扰敌人", dice_sides=2, outcomes={(1,1): strawman, (2,2): strawman}),
    Card("周末偷懒", "可能让敌人跳过回合", dice_sides=7, outcomes={(1,7): weekend}),
    Card("慢速药", "使自己掷骰变慢", stable_effect=slow_down),
    Card("加速药", "使自己掷骰变快", stable_effect=speed_up)
] * 2

# ====== 对局 ======
def game_demo():
    p1 = Player("玩家A", deck_template)
    p2 = Player("玩家B", deck_template)

    # 初始抽牌
    p1.draw(5)
    p2.draw(5)

    turn = 0
    while True:
        current = p1 if turn % 2 == 0 else p2
        enemy = p2 if turn % 2 == 0 else p1

        # 清理上一回合的临时标记（演示用）
        for pl in (current, enemy):
            pl._next_card_invalid = getattr(pl, "_next_card_invalid", False)
            pl._next_card_amplified = getattr(pl, "_next_card_amplified", False)
            pl._skip_next_turn = getattr(pl, "_skip_next_turn", False)

        print("\n===== 回合开始 =====")
        print(current.status())
        print(enemy.status())

        # 检查敌人是否被标记跳过回合（由上回合对方卡牌设置）
        if getattr(current, "_skip_next_turn", False):
            print(f"{current.name} 被迫跳过本回合（受效果影响）")
            # 清掉标记
            current._skip_next_turn = False
            # 抽牌并进入下一玩家
            current.draw(1)
            turn += 1
            continue

        # 本回合行动次数
        ap = current.actions
        for i in range(ap):
            if not current.hand:
                current.draw(1)
                if not current.hand:
                    print("手牌耗尽，无法出牌")
                    break

            print("\n手牌：")
            for idx, card in enumerate(current.hand):
                print(f"{idx+1}. {card.name} - {card.description}")

            try:
                choice = int(input(f"选择要出的牌编号（行动 {i+1}/{ap}，输入0跳过）：")) - 1
            except:
                choice = -1
            if choice == -1:
                print("选择跳过。")
                break

            # 如果目标被标记“下一张牌无效”，则直接消耗但效果为无
            if getattr(enemy, "_next_card_invalid", False) and current.hand and 0 <= choice < len(current.hand):
                # 将那张牌移至弃牌堆并报告被无效
                card = current.hand.pop(choice)
                current.discard.append(card)
                print(f"▶️ 牌被稻草人效果无效化：{card.name}（已弃）")
                # 清掉无效标记（只影响一张）
                enemy._next_card_invalid = False
                # 检查生命状态继续
                continue

            result = current.play_card(choice, enemy)
            print(result)
            if enemy.is_dead():
                print(f"\n💀 {enemy.name} 倒下，{current.name} 获胜！")
                return

        # 回合结束抽牌
        current.draw(1)
        turn += 1


# ====== 运行 ======
if __name__ == "__main__":
    print("交互式骰子演示（终端闪现）已启用：" , INTERACTIVE_DICE)
    print("提示：当出现闪现时按回车停止取值。你可以用“慢速药/加速药”改变自己掷骰的闪现速度。")
    game_demo()

