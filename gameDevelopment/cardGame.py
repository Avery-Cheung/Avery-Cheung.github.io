import random

# ====== 基础系统 ======
class Dice:
    @staticmethod
    def roll(sides, times=1):
        if sides < 1 or times < 1:
            raise ValueError("骰子参数错误：必须 sides>=1, times>=1")
        return [random.randint(1, sides) for _ in range(times)]


class Card:
    def __init__(self, name, description, dice_sides=None, outcomes=None, stable_effect=None):
        self.name = name
        self.description = description
        self.dice_sides = dice_sides
        self.outcomes = outcomes or {}
        self.stable_effect = stable_effect

    def play(self, user, target):
        if self.dice_sides:
            roll = Dice.roll(self.dice_sides, 1)[0]
            for rng, effect in self.outcomes.items():
                if rng[0] <= roll <= rng[1]:
                    return effect(user, target, roll)
            return f"{self.name} 骰到 {roll} → 没有结果"
        elif self.stable_effect:
            return self.stable_effect(user, target)
        return f"{self.name} 没有定义效果"


class Player:
    def __init__(self, name, deck):
        self.name = name
        self.hp = 10
        self.san = 10
        self.deck = deck[:]  # 原始牌堆
        random.shuffle(self.deck)
        self.hand = []
        self.discard = []

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
        return f"{self.name} 状态 → HP:{self.hp} SAN:{self.san} 行动力:{self.actions} 手牌:{[c.name for c in self.hand]}"


# ====== 卡牌效果 ======
def normal_attack(user, target):
    target.hp -= 1
    return f"{user.name} 普通攻击 → {target.name} -1 HP"

def blood_attack(user, target, roll):
    if roll <= 4:
        target.hp -= 3
        user.san -= 1
        return f"{user.name} 血祭猛攻 成功 → {target.name} -3 HP，自身 -1 SAN"
    else:
        user.san -= 2
        return f"{user.name} 血祭猛攻 失败 → 自身 -2 SAN"

def strawman(user, target, roll):
    if roll == 1:
        return f"{user.name} 稻草人 → 使 {target.name} 下一张牌无效"
    else:
        return f"{user.name} 稻草人 → 放大 {target.name} 下一张牌效果（演示）"

def weekend(user, target, roll):
    if roll in [6, 7]:
        return f"{user.name} 周末偷懒 → {target.name} 下回合跳过"
    else:
        return f"{user.name} 周末偷懒 → 什么都没发生"


# ====== 牌库 ======
deck_template = [
    Card("普通攻击", "造成 1 HP", stable_effect=normal_attack),
    Card("血祭猛攻", "高伤害但有风险", dice_sides=6, outcomes={(1,6): blood_attack}),
    Card("稻草人谬误", "概率干扰敌人", dice_sides=2, outcomes={(1,1): strawman, (2,2): strawman}),
    Card("周末偷懒", "可能让敌人跳过回合", dice_sides=7, outcomes={(1,7): weekend})
]*2  # 每张牌两份

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

        print("\n===== 回合开始 =====")
        print(current.status())
        print(enemy.status())

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
    game_demo()