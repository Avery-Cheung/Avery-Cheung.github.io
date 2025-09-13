import random
import threading
import time
import sys
import math

# ====== 配置 ======
INTERACTIVE_DICE = True  # 是否启用终端闪现交互式骰子
DEFAULT_DICE_SPEED = 0.12  # 默认闪现间隔（秒），数值越小变化越快
DEFAULT_DECK_SIZE = 12  # 每副牌的目标牌数（可调整）

# ====== 基础系统 ======
class Dice:
    @staticmethod
    def roll(sides, times=1):
        if sides < 1 or times < 1:
            raise ValueError("骰子参数错误：必须 sides>=1, times>=1")
        return [random.randint(1, sides) for _ in range(times)]

def interactive_roll(sides: int, player, hint: str = None):
    # 如果不是交互式终端（Colab/iPad Notebook 会返回 False），就直接返回随机数（健壮处理）
    if not INTERACTIVE_DICE or not sys.stdin or not sys.stdin.isatty():
        return random.randint(1, sides)

    stop_event = threading.Event()
    result = [random.randint(1, sides)]

    def flicker():
        speed = max(0.01, getattr(player, "dice_speed", DEFAULT_DICE_SPEED))
        while not stop_event.is_set():
            speed = max(0.01, getattr(player, "dice_speed", DEFAULT_DICE_SPEED))
            n = random.randint(1, sides)
            result[0] = n
            sys.stdout.write(f"\r骰子 [{sides}] 闪现: {n}   ")
            sys.stdout.flush()
            time.sleep(speed)
        sys.stdout.write("\r")
        sys.stdout.flush()

    thread = threading.Thread(target=flicker, daemon=True)
    thread.start()

    prompt = "(按回车停止闪现)"
    if hint:
        prompt = f"{hint} {prompt}"
    try:
        input(prompt)
    except KeyboardInterrupt:
        pass
    stop_event.set()
    thread.join(timeout=1.0)
    roll = result[0]
    print(f"\n最终判定 → {roll}")
    return roll

# ====== Card / Player / Deck 系统 ======
class Card:
    def __init__(self, name, description, dice_sides=None, outcomes=None, stable_effect=None, rarity=50):
        self.name = name
        self.description = description
        self.dice_sides = dice_sides
        self.outcomes = outcomes or {}
        self.stable_effect = stable_effect
        self.rarity = int(max(0, min(100, rarity)))  # 0-100，越大越稀有

    def play(self, user, target):
            
        # 获取原始结果
        result = None
        if self.dice_sides:
            result = self._resolve_outcome(user, target, self.outcomes, self.dice_sides)
        elif self.stable_effect:
            result = self.stable_effect(user, target)
        else:
            return f"{self.name} 没有定义效果"
            





                
                
                
                
                    


            
        return result

    def _resolve_outcome(self, user, target, outcomes, dice_sides):
        roll = None
        try:
            roll = interactive_roll(dice_sides, user, hint=f"正在掷 {self.name}（范围 1-{dice_sides}）")
        except Exception:
            roll = random.randint(1, dice_sides)

        for rng, effect in outcomes.items():
            if rng[0] <= roll <= rng[1]:
                if callable(effect):
                    return effect(user, target, roll)
                elif isinstance(effect, dict):
                    return self._resolve_outcome(user, target, effect, dice_sides)
                else:
                    return f"{self.name} 无效效果定义"
        return f"{self.name} 骰到 {roll} → 没有匹配的结果（健壮处理）"

    def clone(self):
        # 浅拷贝一个新的 Card 实例（保证牌堆中每张卡牌实例独立）
        return Card(
            name=self.name,
            description=self.description,
            dice_sides=self.dice_sides,
            outcomes=self.outcomes,
            stable_effect=self.stable_effect,
            rarity=self.rarity
        )

class Player:
    def __init__(self, name, deck):
        self.name = name
        self.hp = 10  # 生命值，上限为10
        self.san = 10  # 理智值，上限为10
        # HP和SAN的中间变量系统
        # 这些变量用于临时存储伤害或恢复效果，在调用apply_modifiers()方法时才会实际应用到hp和san上
        # 这样设计可以确保所有效果在同一时间点应用，避免顺序问题
        self._hp_modifier = 0  # HP修改器，正值表示恢复，负值表示伤害
        self._san_modifier = 0  # SAN修改器，正值表示恢复，负值表示伤害
        # 初始化时直接存储基础行动力，不使用属性设置
        self._base_actions = max(2, self.hp // 2)
        self._negative_action_points = 0  # 用于负行动力累积
        self.deck = deck[:]  # deck 已经是实例列表
        random.shuffle(self.deck)
        self.hand = []
        self.discard = []
        self.dice_speed = DEFAULT_DICE_SPEED

    @property
    def actions(self):
        # 行动力 = 基础行动力 - 负行动力
        return max(0, self._base_actions - getattr(self, "_negative_action_points", 0))

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
        # 考虑中间变量的实际HP和SAN值
        actual_hp = self.hp + self._hp_modifier
        actual_san = self.san + self._san_modifier
        return actual_hp <= 0 or actual_san <= 0

    def apply_modifiers(self):
        """应用HP和SAN的修改器，更新实际值
        
        此方法将中间变量(_hp_modifier和_san_modifier)的值应用到实际的hp和san属性上，
        并显示变化前后的数值对比。应用后会重置中间变量，并确保数值不超过上限。
        """
        # 记录变化前的数值
        old_hp = self.hp
        old_san = self.san
        
        # 应用修改器
        self.hp += self._hp_modifier
        self.san += self._san_modifier
        
        # 确保HP和SAN不超过上限
        self.hp = min(10, self.hp)
        self.san = min(10, self.san)
        
        # 如果有变化，显示变化信息
        if old_hp != self.hp or old_san != self.san:
            hp_change = self.hp - old_hp
            san_change = self.san - old_san
            change_info = f"{self.name} 属性变化: "
            if hp_change != 0:
                change_info += f"HP {old_hp}→{self.hp} ({hp_change:+d}) "
            if san_change != 0:
                change_info += f"SAN {old_san}→{self.san} ({san_change:+d})"
            print(change_info)
        
        # 重置修改器
        self._hp_modifier = 0
        self._san_modifier = 0
    
    def status(self):
        # 考虑中间变量的实际HP和SAN值
        actual_hp = self.hp + self._hp_modifier
        actual_san = self.san + self._san_modifier
        return f"{self.name} 状态 → HP:{actual_hp} SAN:{actual_san} 行动力:{self.actions} 手牌:{[c.name for c in self.hand]} (闪现速:{self.dice_speed:.3f}s)"

# ====== 卡牌效果 ======
def normal_attack(user, target):
    target._hp_modifier -= 1  # 使用中间变量
    return f"{user.name} 普通攻击 → {target.name} -1 HP"

def blood_attack(user, target, roll):
    if 1 <= roll <= 4:
        target._hp_modifier -= 3  # 使用中间变量
        user._san_modifier -= 1  # 使用中间变量
        return f"{user.name} 血祭猛攻 成功（{roll}）→ {target.name} -3 HP，自身 -1 SAN"
    else:
        user._san_modifier -= 2  # 使用中间变量
        return f"{user.name} 血祭猛攻 失败（{roll}）→ 自身 -2 SAN"


def weekend(user, target, roll):
    if roll in [6, 7]:
        target._skip_next_turn = True
        return f"{user.name} 周末偷懒（{roll}）→ {target.name} 跳过下回合"
    else:
        return f"{user.name} 周末偷懒（{roll}）→ 什么都没发生"

def slow_down(user, target):
    user.dice_speed *= 1.6
    return f"{user.name} 使用 慢速药 → 本人掷骰闪现变慢（{user.dice_speed:.3f}s）"

def speed_up(user, target):
    target.dice_speed = max(0.02, target.dice_speed * 0.5)  # 加速对手的骰子（向下限靠拢）
    return f"{user.name} 使用 加速药 → {target.name} 掷骰闪现变快（{target.dice_speed:.3f}s）"

# ====== 新增特殊卡牌效果 ======
def mentos_god(user, target, roll):
    # 两次判定：第一次回SAN，第二次回血
    results = []
    
    # 第一次判定：回SAN
    if 1 <= roll <= 4:
        amount = 1
    elif 5 <= roll <= 6:
        amount = 2
    else:  # roll == 7
        amount = 3
    
    # 检查是否超过SAN上限
    current_san = user.san + user._san_modifier  # 考虑中间变量
    actual_amount = min(amount, 10 - current_san)
    if actual_amount > 0:
        user._san_modifier += actual_amount  # 使用中间变量
        results.append(f"第一次判定 → 恢复 {actual_amount} SAN")
    else:
        results.append(f"第一次判定 → SAN已满，无法恢复")
    
    # 第二次判定：回血
    roll2 = random.randint(1, 7)
    if 1 <= roll2 <= 4:
        amount = 1
    elif 5 <= roll2 <= 6:
        amount = 2
    else:  # roll2 == 7
        amount = 3
    
    # 检查是否超过HP上限
    current_hp = user.hp + user._hp_modifier  # 考虑中间变量
    actual_amount = min(amount, 10 - current_hp)
    if actual_amount > 0:
        user._hp_modifier += actual_amount  # 使用中间变量
        results.append(f"第二次判定 → 恢复 {actual_amount} HP")
    else:
        results.append(f"第二次判定 → HP已满，无法恢复")
    
    return f"{user.name} 使用 曼妥思之神\n" + "\n".join(results)

def turtle_300(user, target, roll):
    if roll == 300:
        # 玩家选择对方一个数值-300
        choice = None
        while choice not in ["hp", "san", "actions"]:
            choice = input(f"{user.name} 骰到300！选择减少 {target.name} 的数值 (hp/san/actions): ").strip().lower()
        if choice == "hp":
            target._hp_modifier -= 300  # 使用中间变量
        elif choice == "san":
            target._san_modifier -= 300  # 使用中间变量
        elif choice == "actions":
            # 负行动力累积
            target._negative_action_points = getattr(target, "_negative_action_points", 0) + 300
        return f"{user.name} 强制 {target.name} {choice}-300！"
    else:
        return f"{user.name} 出 300龟失败，骰到 {roll} → 无效"

# ====== 牌库原型模板（每种卡只定义一次，下面会根据 rarity 生成具体副本） ======
deck_prototypes = [
    Card("普通攻击", "造成 1 HP", stable_effect=normal_attack, rarity=20),
    Card("血祭猛攻", "高伤害但有风险", dice_sides=6, outcomes={(1,6): blood_attack}, rarity=60),

    Card("周末偷懒", "可能让敌人跳过回合", dice_sides=7, outcomes={(1,7): weekend}, rarity=70),
    Card("慢速药", "使自己掷骰变慢", stable_effect=slow_down, rarity=40),
    Card("加速药", "使自己掷骰变快", stable_effect=speed_up, rarity=40),
    Card("曼妥思之神", "纯回血与SAN", dice_sides=7, outcomes={(1,7): mentos_god}, rarity=30),
    Card("300龟", "骰到300可强制选择对方数值-300", dice_sides=300, outcomes={(300,300): turtle_300}, rarity=80)
]

# ====== 构建牌堆函数（根据 rarity 计算每种卡的副本数） ======
def build_deck_from_prototypes(prototypes, deck_size=DEFAULT_DECK_SIZE):
    """
    根据信赖度生成一副牌（返回 Card 实例列表）
    权重用 (100 - rarity)，稀有度越高权重越小。
    我们按期望值分配副本数，然后按小数部分分配剩余格子。
    """
    weights = [max(1, 100 - p.rarity) for p in prototypes]  # 避免为 0
    total_weight = sum(weights)
    # 期望副本（浮点）
    expected = [(w / total_weight) * deck_size for w in weights]
    # 先取 floor
    copies = [math.floor(e) for e in expected]
    assigned = sum(copies)
    remaining = deck_size - assigned

    # 按小数部分排序补齐剩余slots
    fractional = [(expected[i] - copies[i], i) for i in range(len(prototypes))]
    fractional.sort(reverse=True)
    idx = 0
    while remaining > 0 and idx < len(fractional):
        i = fractional[idx][1]
        copies[i] += 1
        remaining -= 1
        idx += 1

    # 如果仍有剩余（理论上不会），就随机分配
    while remaining > 0:
        i = random.randrange(len(prototypes))
        copies[i] += 1
        remaining -= 1

    # 如果全部 copies 都为 0（极小概率），退化为至少放 1 张每种卡，直到满足 deck_size
    if sum(copies) == 0:
        for i in range(len(copies)):
            copies[i] = 1
        # 再裁剪或补齐到 deck_size
        while sum(copies) > deck_size:
            # 随机减少一个有副本的项
            j = random.choice([k for k, v in enumerate(copies) if v > 0])
            copies[j] -= 1
        while sum(copies) < deck_size:
            j = random.randrange(len(copies))
            copies[j] += 1

    # 生成 deck（clone 新实例）
    deck = []
    for i, cnt in enumerate(copies):
        for _ in range(int(cnt)):
            deck.append(prototypes[i].clone())
    random.shuffle(deck)
    return deck

# ====== 辅助函数 ======
def effect_status(player):
    effects = []
    if getattr(player, "_skip_next_turn", False):
        effects.append("跳过下回合")
    return ", ".join(effects) if effects else "无"

# ====== 游戏主逻辑 ======
def game_demo(deck_size=DEFAULT_DECK_SIZE):
    # 为双方分别构建牌堆（每局不同）
    p1 = Player("玩家A", build_deck_from_prototypes(deck_prototypes, deck_size=deck_size))
    p2 = Player("玩家B", build_deck_from_prototypes(deck_prototypes, deck_size=deck_size))

    p1.draw(5)
    p2.draw(5)

    turn = 0
    first_player = p1  # 记录先手玩家

    while True:
        current = p1 if turn % 2 == 0 else p2
        enemy = p2 if turn % 2 == 0 else p1

        # 初始化状态标记（确保属性存在）
        for pl in (current, enemy):
            pl._skip_next_turn = getattr(pl, "_skip_next_turn", False)
            pl._negative_action_points = getattr(pl, "_negative_action_points", 0)  # 负行动力补丁

        # 每回合行动力减去负数储存值
        if getattr(current, "_negative_action_points", 0) > 0:
            if current.actions <= 0:
                print(f"{current.name} 行动力不足（负数效果），跳过回合")
                current._negative_action_points = max(0, current._negative_action_points - current.actions)
                current.draw(1)
                turn += 1
                continue

        # --- 回合信息提示 ---
        print(f"\n===== 回合 {turn + 1} =====")
        print(f"先手玩家: {first_player.name} | 当前回合: {current.name}")
        print("----------------------------")
        print(f"{current.name} 状态 → HP:{current.hp} SAN:{current.san} 行动力:{current.actions} "
              f"手牌数:{len(current.hand)} 牌库:{len(current.deck)} 弃牌堆:{len(current.discard)} "
              f"效果:{effect_status(current)} (闪现速:{current.dice_speed:.3f}s)")
        print(f"{enemy.name} 状态 → HP:{enemy.hp} SAN:{enemy.san} 行动力:{enemy.actions} "
              f"手牌数:{len(enemy.hand)} 牌库:{len(enemy.deck)} 弃牌堆:{len(enemy.discard)} "
              f"效果:{effect_status(enemy)} (闪现速:{enemy.dice_speed:.3f}s)")
        

        # 处理跳过回合状态
        if getattr(current, "_skip_next_turn", False):
            print(f"{current.name} 被迫跳过本回合（受效果影响）")
            current._skip_next_turn = False
            current.draw(1)
            turn += 1
            continue

        # 本回合行动次数
        actions_remaining = current.actions
        
        # 当还有行动力时，可以继续出牌
        while actions_remaining > 0:
            print(f"\n剩余行动力: {actions_remaining}")
            print(f"{current.name} 手牌: {[f'{i}:{c.name}' for i,c in enumerate(current.hand)]}")
            
            # 如果没有手牌，自动抽一张并结束回合
            if not current.hand:
                print("没有手牌，自动抽一张牌")
                current.draw(1)
                actions_remaining = 0  # 用掉所有行动力
                break
                
            # 提供选项：出牌或结束回合
            choice = input(f"选择要使用的卡牌编号(0-{len(current.hand)-1})，或输入-1结束回合: ").strip()
            
            if choice == "-1":
                print("选择结束回合")
                break
                
            try:
                idx = int(choice)
                if 0 <= idx < len(current.hand):
                    # 出牌
                    result = current.play_card(idx, enemy)
                    print(result)
                    
                    # 立即应用伤害修改器，使伤害生效
                    current.apply_modifiers()
                    enemy.apply_modifiers()
                    
                    actions_remaining -= 1  # 每出一张牌消耗一点行动力
                    
                    # 检查胜负
                    if current.is_dead():
                        print(f"{current.name} 已死亡，{enemy.name} 获胜！")
                        input("按回车返回主菜单...")
                        return
                    if enemy.is_dead():
                        print(f"{enemy.name} 已死亡，{current.name} 获胜！")
                        input("按回车返回主菜单...")
                        return
                else:
                    print("编号无效，请重新选择。")
            except ValueError:
                print("请输入数字编号或-1结束回合。")
        
        # 回合结束抽牌（每回合抽一张）
        current.draw(1)
        turn += 1

# ====== 主菜单 ======
def main_menu():
    while True:
        print("\n===== 欢迎来到卡牌游戏 =====")
        print("1. 开始新游戏（默认牌堆大小 12）")
        print("2. 开始新游戏（自定义牌堆大小）")
        print("3. 退出游戏")
        choice = input("请选择操作 (1/2/3): ").strip()

        if choice == "1":
            game_demo(deck_size=DEFAULT_DECK_SIZE)
        elif choice == "2":
            try:
                n = int(input("输入每副牌的目标牌数（建议 8-30）: ").strip())
                n = max(4, min(60, n))
                game_demo(deck_size=n)
            except ValueError:
                print("输入无效，返回菜单。")
        elif choice == "3":
            print("退出游戏，再见！")
            sys.exit(0)
        else:
            print("无效选择，请重新输入。")

# ====== 启动程序 ======
if __name__ == "__main__":
    main_menu()

# ====== 更新日志 ======

# v1.2.0
# [更新1] 在 Card 类新增参数 rarity（0-100，数值越大越稀有）
# [更新2] 新增 Card.clone 方法，用于生成牌堆中独立实例
# [更新3] 新增 build_deck_from_prototypes 函数：根据信赖度 (100 - rarity) 计算权重，
#         并按期望值分配每种卡在牌堆中的副本数（目标牌堆大小可配置，默认为 12）
# [更新4] 将原先的 deck_template 改为 deck_prototypes（每种卡只定义一次并包含 rarity）
# [更新5] Player 初始化现在接收已经构建好的牌堆（每局会为双方单独构建）
# [更新6] 在主菜单加入“自定义牌堆大小”选项，方便调试稀有度效果
# [更新7] 保留了之前所有功能：交互闪现骰子、回合信息/效果显示、跳过回合逻辑、胜负后返回主菜单等
# [更新8] 增加负行动力机制：出牌前减去负行动力，可以跳过多个回合
# [更新9] 新增曼妥思之神卡牌（双判定回血/回SAN）
# [更新10] 新增300龟机制杀卡牌（骰到300可强制扣除对方数值）
# [更新11] 修复加速药的作用，时期能增加对方骰子的速度而不是己方的

# v1.2.1
# [更新1] 暂时移除了谬误稻草人
# [更新2] 新增控制血量和san变化的中间变量, 方便后续如谬误稻草人一类卡牌功能的实现
# [更新3] 调整了更清晰的状态改变显示
