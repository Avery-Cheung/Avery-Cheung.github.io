
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
    def roll(sides, times=1, min_value=1):
        if sides < 1 or times < 1 or min_value < 1:
            raise ValueError("骰子参数错误：必须 sides>=1, times>=1, min_value>=1")
        if min_value > sides:
            raise ValueError("骰子参数错误：min_value 不能大于 sides")
        return [random.randint(min_value, sides) for _ in range(times)]

def interactive_roll(sides: int, player, hint: str = None, min_value=1):
    # 检查玩家是否有预设的骰子值
    if hasattr(player, '_next_roll_value'):
        preset_value = getattr(player, '_next_roll_value')
        # 确保预设值在有效范围内
        if min_value <= preset_value <= sides:
            # 使用预设值并清除属性
            delattr(player, '_next_roll_value')
            print(f"骰子 [{min_value}-{sides}] 闪现: {preset_value}    ")
            print(f"\n最终判定 → {preset_value} (预设值)")
            return preset_value
        else:
            # 预设值无效，清除属性并继续正常流程
            delattr(player, '_next_roll_value')
            print(f"预设值 {preset_value} 超出范围 [{min_value}-{sides}]，将使用随机值")

    # 如果不是交互式终端（Colab/iPad Notebook 会返回 False），就直接返回随机数（健壮处理）
    if not INTERACTIVE_DICE or not sys.stdin or not sys.stdin.isatty():
        return random.randint(min_value, sides)

    stop_event = threading.Event()
    result = [random.randint(min_value, sides)]

    def flicker():
        speed = max(0.01, getattr(player, "dice_speed", DEFAULT_DICE_SPEED))
        # 检查是否有裘罗效果
        has_qiu_luo = getattr(player, "_qiu_luo_effect", False)
        # 乱码字符序列
        garbled_chars = "!@#$%^&*?"
        char_index = 0

        while not stop_event.is_set():
            speed = max(0.01, getattr(player, "dice_speed", DEFAULT_DICE_SPEED))
            n = random.randint(min_value, sides)
            result[0] = n

            if has_qiu_luo:
                # 显示乱码而不是数字
                display_char = garbled_chars[char_index % len(garbled_chars)]
                sys.stdout.write(f"\r骰子 [{min_value}-{sides}] 闪现: {display_char}   ")
                char_index += 1
            else:
                sys.stdout.write(f"\r骰子 [{min_value}-{sides}] 闪现: {n}   ")
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

    # 检查是否有裘罗效果
    has_qiu_luo = getattr(player, "_qiu_luo_effect", False)
    if has_qiu_luo:
        # 显示乱码判定结果
        print(f"\n最终判定 → !@#$%^&*?")
        # 清除裘罗效果，使其只生效一次
        delattr(player, "_qiu_luo_effect")
    else:
        print(f"\n最终判定 → {roll}")

    return roll

# ====== Card / Player / Deck 系统 ======
class Card:
    def __init__(self, name, description, dice_sides=None, outcomes=None, stable_effect=None, rarity=50, min_value=1):
        self.name = name
        self.description = description
        self.dice_sides = dice_sides
        self.outcomes = outcomes or {}
        self.stable_effect = stable_effect
        self.rarity = int(max(0, min(100, rarity)))  # 0-100，越大越稀有
        self.min_value = min_value  # 保存min_value参数

    def play(self, user, target):

        # 获取原始结果
        result = None
        if self.dice_sides:
            result = self._resolve_outcome(user, target, self.outcomes, self.dice_sides, self.min_value)
        elif self.stable_effect:
            result = self.stable_effect(user, target)
        else:
            return f"{self.name} 没有定义效果"
        return result

    def _resolve_outcome(self, user, target, outcomes, dice_sides, min_value=1):
        roll = None
        try:
            roll = interactive_roll(dice_sides, user, hint=f"正在掷 {self.name}（范围 {min_value}-{dice_sides}）", min_value=min_value)
        except Exception:
            roll = random.randint(min_value, dice_sides)

        # 检查是否有虚环之匣的递归效果
        recursion_count = getattr(user, "_void_box_recursion", 0)

        # 如果有递归效果且骰子在某个范围内，需要进行递归判定
        if recursion_count > 0:
            for rng, effect in outcomes.items():
                if rng[0] <= roll <= rng[1]:
                    # 在有效范围内，需要递归判定
                    print(f"{user.name} 受到虚环之匣影响，需要再投 {recursion_count} 次骰子确认效果")

                    # 记录原始结果
                    original_roll = roll
                    valid_rolls = 1  # 原始骰子已经算一次有效

                    # 进行递归判定
                    for i in range(recursion_count):
                        try:
                            recursive_roll = interactive_roll(dice_sides, user, hint=f"虚环之匣递归判定 {i+1}/{recursion_count}（范围 {min_value}-{dice_sides}）", min_value=min_value)
                        except Exception:
                            recursive_roll = random.randint(min_value, dice_sides)

                        # 检查递归骰子是否在相同范围内
                        if rng[0] <= recursive_roll <= rng[1]:
                            valid_rolls += 1
                            print(f"第 {i+1} 次递归判定: {recursive_roll} (在有效范围内 {rng[0]}-{rng[1]})")
                        else:
                            print(f"第 {i+1} 次递归判定: {recursive_roll} (不在有效范围内 {rng[0]}-{rng[1]})")

                    # 清除递归效果
                    delattr(user, "_void_box_recursion")

                    # 如果所有递归判定都在有效范围内，才触发效果
                    if valid_rolls > recursion_count // 2:  # 超过一半的递归判定在有效范围内
                        print(f"递归判定通过（{valid_rolls}/{recursion_count+1}），效果生效")
                        if callable(effect):
                            return effect(user, target, original_roll)
                        elif isinstance(effect, dict):
                            return self._resolve_outcome(user, target, effect, dice_sides, min_value)
                        else:
                            return f"{self.name} 无效效果定义"
                    else:
                        return f"{self.name} 骰到 {original_roll} → 递归判定未通过（{valid_rolls}/{recursion_count+1}），效果无效"

            # 如果不在任何范围内，清除递归效果并返回正常结果
            delattr(user, "_void_box_recursion")
            return f"{self.name} 骰到 {roll} → 没有匹配的结果（健壮处理）"

        # 正常情况下的效果处理
        for rng, effect in outcomes.items():
            if rng[0] <= roll <= rng[1]:
                if callable(effect):
                    return effect(user, target, roll)
                elif isinstance(effect, dict):
                    return self._resolve_outcome(user, target, effect, dice_sides, min_value)
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
            rarity=self.rarity,
            min_value=self.min_value
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
        return self._base_actions - getattr(self, "_negative_action_points", 0)

    def display_actions(self):
        # 用于显示的行动力，如果是负数则显示为0
        return max(0, self.actions())

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



# ====== 卡牌函数 ======
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
    if 1 <= roll <= 2:
        amount = 0  # 不恢复SAN
    elif 3 <= roll <= 4:
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
    try:
        roll2 = interactive_roll(7, user, hint=f"曼妥思之神 第二次判定（回血）")
    except Exception:
        roll2 = random.randint(1, 7)

    if 1 <= roll2 <= 2:
        amount = 0  # 不恢复HP
    elif 3 <= roll2 <= 4:
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
            # 直接设置负行动力为300，而不是累加
            target._negative_action_points = 300
        return f"{user.name} 强制 {target.name} {choice}-300！"
    else:
        return f"{user.name} 300龟（{roll}）→ 什么都没发生"

def debug_card(user, target):
    # 调试卡牌：让玩家选择下一张打出的牌的点数
    try:
        print(f"{user.name} 使用了调试卡牌！")
        value = int(input("请输入下一张牌的点数（必须是整数）："))
        # 设置一个全局变量或用户属性来存储这个值
        user._next_roll_value = value
        return f"{user.name} 设置了下一张牌的点数为 {value}"
    except ValueError:
        return f"{user.name} 调试卡牌使用失败：输入的不是有效整数"
    except Exception as e:
        return f"{user.name} 调试卡牌使用失败：{str(e)}"

def twilight_lizard(user, target, roll):
    if 14 <= roll <= 17:
        target._hp_modifier -= 1  # 使用中间变量
        return f"{user.name} 暮光巫蜥（{roll}）→ {target.name} -1 HP"
    elif 18 <= roll <= 19:
        target._hp_modifier -= 4  # 使用中间变量
        return f"{user.name} 暮光巫蜥（{roll}）→ {target.name} -4 HP"
    elif 20 <= roll <= 24:
        target._hp_modifier -= 2  # 使用中间变量
        return f"{user.name} 暮光巫蜥（{roll}）→ {target.name} -2 HP"
    else:
        return f"{user.name} 暮光巫蜥（{roll}）→ 无效点数，没有效果"

def chicken_machine(user, target):
    # 当前回合效果：-2san
    user._san_modifier -= 2
    
    # 设置延迟效果：在四回合后开始时+5san
    # 我们需要在玩家对象上存储这个延迟效果
    # 使用一个列表来存储所有延迟效果，每个效果是一个元组(生效回合数, 效果函数)
    if not hasattr(user, '_delayed_effects'):
        user._delayed_effects = []
    
    # 延迟效果将在4个回合后生效（当前回合是0，下一回合是1，下下回合是2，下下下回合是3，第四回合是4）
    # 我们存储(生效的回合数, 效果函数)
    def add_san_effect():
        user._san_modifier += 5
        return f"{user.name} 的鸡机效果触发 → +5 SAN"
    
    # 获取当前回合数
    current_turn = getattr(user, '_current_turn', 0)
    user._delayed_effects.append((current_turn + 4, add_san_effect))
    
    return f"{user.name} 使用 鸡机 → -2 SAN，四回合后 +5 SAN"

def glasses_frog_effect(user, target, roll):
    if 1 <= roll <= 5:
        # 看片效果：加2san
        user._san_modifier += 2
        return f"{user.name} 眼镜蛙（{roll}）→ 看片 +2 SAN"
    elif 6 <= roll <= 10:
        # 飞踢效果：扣对方两次1hp
        target._hp_modifier -= 1
        first_hit = f"{user.name} 眼镜蛙（{roll}）→ 飞踢 {target.name} -1 HP（第一次）"
        target._hp_modifier -= 1
        second_hit = f"{user.name} 眼镜蛙（{roll}）→ 飞踢 {target.name} -1 HP（第二次）"
        return f"{first_hit}\n{second_hit}"
    else:
        return f"{user.name} 眼镜蛙（{roll}）→ 无效点数，没有效果"

def qiu_luo_effect(user, target):
    # 裘罗效果：让对方下一次投骰子闪现的数字变成乱码循环
    # 在玩家对象上设置一个属性来标记这个效果
    target._qiu_luo_effect = True
    return f"{user.name} 使用 裘罗 → {target.name} 的下一次骰子将显示乱码"

def void_box_effect(user, target, roll):
    # 虚环之匣效果：让对方下次投骰子判定时要递归n次
    # 根据骰子值确定递归次数
    if roll == 1:
        n = 0  # 不递归
    elif 2 <= roll <= 4:
        n = 1  # 递归一次
    else:  # roll == 5
        n = 2  # 递归两次

    # 在玩家对象上设置递归效果属性
    target._void_box_recursion = n
    return f"{user.name} 使用 虚环之匣（{roll}）→ {target.name} 的下一次判定需要递归 {n} 次"

def blood_armor_snail(user, target):
    # 血甲蜗效果：造成已损失血量/2(向下取整)的伤害，然后投骰子，1-10，骰到10时追加上回合损失血量/3(向下取整)的伤害并扣除自己与之相同的san
    
    # 计算已损失血量
    lost_hp = 10 - user.hp  # 最大HP为10
    
    # 计算基础伤害：已损失血量/2(向下取整)
    base_damage = lost_hp // 2
    target._hp_modifier -= base_damage
    result = f"{user.name} 血甲蜗 → {target.name} -{base_damage} HP (已损失血量/2)"
    
    # 投骰子判定追加效果
    try:
        roll = interactive_roll(10, user, hint=f"血甲蜗 追加效果判定（1-10）")
    except Exception:
        roll = random.randint(1, 10)
    
    # 如果骰到10，触发追加效果
    if roll == 10:
        # 获取上回合损失血量
        last_turn_lost_hp = getattr(user, "_last_turn_lost_hp", 0)
        
        # 计算追加伤害：上回合损失血量/3(向下取整)
        extra_damage = last_turn_lost_hp // 3
        target._hp_modifier -= extra_damage
        user._san_modifier -= extra_damage
        
        result += f"\n追加效果（骰到{roll}）→ {target.name} -{extra_damage} HP，自身 -{extra_damage} SAN (上回合损失血量/3)"
    else:
        result += f"\n追加效果（骰到{roll}）→ 无追加效果"
    
    # 记录当前回合损失的血量，供下回合使用
    # 注意：这里使用的是当前回合开始时的HP，而不是应用效果后的HP
    user._last_turn_lost_hp = lost_hp
    
    return result

# ====== 牌库原型模板（每种卡只定义一次，下面会根据 rarity 生成具体副本） ======
deck_prototypes = [
    Card("普通攻击", "造成 1 HP", stable_effect=normal_attack, rarity=20),
    Card("血祭猛攻", "高伤害但有风险", dice_sides=6, outcomes={(1,6): blood_attack}, rarity=60),

    Card("周末偷懒", "可能让敌人跳过回合", dice_sides=7, outcomes={(1,7): weekend}, rarity=70),
    Card("慢速药", "使自己掷骰变慢", stable_effect=slow_down, rarity=40),
    Card("加速药", "使自己掷骰变快", stable_effect=speed_up, rarity=40),
    Card("曼妥思之神", "纯回血与SAN", dice_sides=7, outcomes={(1,7): mentos_god}, rarity=30),
    Card("300龟", "骰到300可强制选择对方数值-300", dice_sides=300, outcomes={(300,300): turtle_300}, rarity=80),
    Card("调试卡牌", "可设置下一张牌的点数", stable_effect=debug_card, rarity=1),
    Card("暮光巫蜥", "14-16:扣1HP, 17-19:扣4HP, 20-24:扣2HP", dice_sides=24, outcomes={(14,16): twilight_lizard, (17,19): twilight_lizard, (20,24): twilight_lizard}, min_value=14, rarity=50),
    Card("鸡机", "当前回合-2SAN，四回合后+5SAN", stable_effect=chicken_machine, rarity=65),
    Card("眼镜蛙", "1-5看片+2SAN, 6-10飞踢-2HP", dice_sides=10, outcomes={(1,10): glasses_frog_effect}, rarity=50),
    Card("裘罗", "使对方下一次骰子显示乱码", stable_effect=qiu_luo_effect, rarity=80),
    Card("虚环之匣", "使对方下次判定需要递归1-3次", dice_sides=5, outcomes={(1,5): void_box_effect}, rarity=10),
    Card("血甲蜗", "造成已损失血量/2的伤害，骰到10时追加上回合损失血量/3的伤害并扣除自己与之相同的san", stable_effect=blood_armor_snail, rarity=75)
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
def apply_delayed_effects(player, current_turn):
    """应用所有到期的延迟效果"""
    if not hasattr(player, '_delayed_effects'):
        return
    
    # 找出所有应该在这个回合生效的效果
    triggered_effects = []
    remaining_effects = []
    
    for effect_turn, effect_func in player._delayed_effects:
        if effect_turn <= current_turn:
            triggered_effects.append(effect_func)
        else:
            remaining_effects.append((effect_turn, effect_func))
    
    # 更新延迟效果列表，移除已触发的
    player._delayed_effects = remaining_effects
    
    # 应用所有触发的效果
    results = []
    for effect in triggered_effects:
        try:
            result = effect()
            if result:
                results.append(result)
        except Exception as e:
            results.append(f"延迟效果应用出错: {str(e)}")
    
    # 如果有触发的效果，打印出来
    if results:
        print("\n===== 延迟效果触发 =====")
        for result in results:
            print(result)
        # 立即应用修改器
        player.apply_modifiers()

def effect_status(player):
    effects = []
    if getattr(player, "_skip_next_turn", False):
        effects.append("跳过下回合")
    
    # 显示延迟效果数量
    delayed_count = len(getattr(player, "_delayed_effects", []))
    if delayed_count > 0:
        effects.append(f"延迟效果({delayed_count})")
        
    return ", ".join(effects) if effects else "无"



# ====== 游戏主逻辑 ======
def game_demo(deck_size=DEFAULT_DECK_SIZE, debug_mode=False):
    # 根据debug_mode参数决定是否包含调试卡牌
    if debug_mode:
        # 包含调试卡牌
        p1 = Player("玩家A", build_deck_from_prototypes(deck_prototypes, deck_size=deck_size))
        p2 = Player("玩家B", build_deck_from_prototypes(deck_prototypes, deck_size=deck_size))
    else:
        # 不包含调试卡牌
        # 创建一个不包含调试卡牌的牌堆原型列表
        filtered_prototypes = [card for card in deck_prototypes if card.name != "调试卡牌"]
        p1 = Player("玩家A", build_deck_from_prototypes(filtered_prototypes, deck_size=deck_size))
        p2 = Player("玩家B", build_deck_from_prototypes(filtered_prototypes, deck_size=deck_size))

    p1.draw(5)
    p2.draw(5)

    # 通过掷骰子决定先手
    print("\n===== 决定先手 =====")
    print("双方将各掷一次骰子，点数高者获得先手！")

    # 玩家A掷骰
    print(f"{p1.name}，准备掷骰子...")
    roll1 = interactive_roll(6, p1, f"{p1.name} 掷骰中")

    # 玩家B掷骰
    print(f"{p2.name}，准备掷骰子...")
    roll2 = interactive_roll(6, p2, f"{p2.name} 掷骰中")

    # 决定先手
    if roll1 > roll2:
        first_player = p1
        print(f"{p1.name} 点数更高，获得先手！")
    elif roll2 > roll1:
        first_player = p2
        print(f"{p2.name} 点数更高，获得先手！")
    else:
        # 平局时再次掷骰
        print("平局！双方再次掷骰...")
        print(f"{p1.name}，准备掷骰子...")
        roll1 = interactive_roll(6, p1, f"{p1.name} 掷骰中")

        print(f"{p2.name}，准备掷骰子...")
        roll2 = interactive_roll(6, p2, f"{p2.name} 掷骰中")

        if roll1 >= roll2:  # 第二次平局时，玩家A优先
            first_player = p1
            print(f"{p1.name} 点数更高或相等，获得先手！")
        else:
            first_player = p2
            print(f"{p2.name} 点数更高，获得先手！")

    input("按回车键开始游戏...")

    turn = 0
    # 根据掷骰结果设置先手玩家
    # 无论谁先手，turn都从0开始，通过first_player记录先手玩家
    first_player = first_player  # 已经通过掷骰子确定了先手玩家

    while True:
        # 根据先手玩家和turn值确定当前玩家
        if first_player == p1:
            current = p1 if turn % 2 == 0 else p2
            enemy = p2 if turn % 2 == 0 else p1
        else:
            current = p2 if turn % 2 == 0 else p1
            enemy = p1 if turn % 2 == 0 else p2

        # 初始化状态标记（确保属性存在）
        for pl in (current, enemy):
            pl._skip_next_turn = getattr(pl, "_skip_next_turn", False)
            pl._negative_action_points = getattr(pl, "_negative_action_points", 0)  # 负行动力补丁
            pl._delayed_effects = getattr(pl, "_delayed_effects", [])  # 延迟效果列表
            pl._current_turn = getattr(pl, "_current_turn", turn)  # 当前回合数

        # 每回合行动力减去负数储存值
        if getattr(current, "_negative_action_points", 0) > 0:
            # 计算本回合可恢复的行动力
            recovery = max(2, current.hp // 2)
            # 减少负行动力，但不超过恢复量
            current._negative_action_points = max(0, current._negative_action_points - recovery)

            if current.actions <= 0:
                print(f"{current.name} 行动力不足（负数效果），跳过回合")
                print(f"{current.name} 恢复了 {recovery} 点负行动力，剩余 {current._negative_action_points} 点")
                current.draw(1)

                # 弃牌环节 - 行动力不足时
                # 计算玩家最多可以保留的牌数（行动力上限，最小为2）
                max_cards = max(2, current._base_actions)

                # 如果手牌数量超过最大保留数量，进入弃牌环节
                if len(current.hand) > max_cards:
                    print(f"\n===== 弃牌环节 =====")
                    print(f"{current.name} 手牌数量({len(current.hand)})超过最大保留数量({max_cards})，需要弃牌")

                    # 不断弃牌直到手牌数量不超过最大保留数量
                    while len(current.hand) > max_cards:
                        print(f"\n{current.name} 手牌: {[f'{i}:{c.name}' for i,c in enumerate(current.hand)]}")
                        print(f"需要弃掉 {len(current.hand) - max_cards} 张牌")

                        try:
                            choice = input(f"选择要弃掉的卡牌编号(0-{len(current.hand)-1}): ").strip()
                            idx = int(choice)

                            if 0 <= idx < len(current.hand):
                                # 弃牌
                                discarded_card = current.hand.pop(idx)
                                current.discard.append(discarded_card)
                                print(f"{current.name} 弃掉了 {discarded_card.name}")
                            else:
                                print("编号无效，请重新选择。")
                        except ValueError:
                            print("请输入数字编号。")

                turn += 1
                continue

        # 更新当前回合数
        current._current_turn = turn
        enemy._current_turn = turn
        
        # 在回合开始时应用延迟效果
        apply_delayed_effects(current, turn)
        apply_delayed_effects(enemy, turn)
        
        # --- 回合信息提示 ---
        # 计算当前回合数：两个玩家各完成一次自己的回合算一个总的回合
        # 无论谁先手，turn=0和1都是第1回合，turn=2和3都是第2回合
        round_num = (turn // 2) + 1

        player_turn = "先手" if current == first_player else "后手"
        print(f"\n===== 第 {round_num} 回合 =====")
        print("----------------------------")
        print(f"{current.name} 状态 → HP:{current.hp} SAN:{current.san} 行动力:{current.actions} "
              f"手牌数:{len(current.hand)} 牌库:{len(current.deck)} 弃牌堆:{len(current.discard)} "
              f"效果:{effect_status(current)} (闪现速:{current.dice_speed:.3f}s)")
        print(f"{enemy.name} 状态 → HP:{enemy.hp} SAN:{enemy.san} 行动力:{enemy.actions} "
              f"手牌数:{len(enemy.hand)} 牌库:{len(enemy.deck)} 弃牌堆:{len(enemy.discard)} "
              f"效果:{effect_status(enemy)} (闪现速:{enemy.dice_speed:.3f}s)")
        print("~~~~~~~~~~~~~~~~~~~~~~~~~~~~")
        print(f"当前行动: {current.name} ({player_turn})")
        print("~~~~~~~~~~~~~~~~~~~~~~~~~~~~")

        # 处理跳过回合状态
        if getattr(current, "_skip_next_turn", False):
            print(f"{current.name} 被迫跳过本回合（受效果影响）")
            current._skip_next_turn = False
            current.draw(1)

            # 弃牌环节 - 跳过回合时
            # 计算玩家最多可以保留的牌数（行动力上限，最小为2）
            max_cards = max(2, current._base_actions)

            # 如果手牌数量超过最大保留数量，进入弃牌环节
            if len(current.hand) > max_cards:
                print(f"\n===== 弃牌环节 =====")
                print(f"{current.name} 手牌数量({len(current.hand)})超过最大保留数量({max_cards})，需要弃牌")

                # 不断弃牌直到手牌数量不超过最大保留数量
                while len(current.hand) > max_cards:
                    print(f"\n{current.name} 手牌: {[f'{i}:{c.name}' for i,c in enumerate(current.hand)]}")
                    print(f"需要弃掉 {len(current.hand) - max_cards} 张牌")

                    try:
                        choice = input(f"选择要弃掉的卡牌编号(0-{len(current.hand)-1}): ").strip()
                        idx = int(choice)

                        if 0 <= idx < len(current.hand):
                            # 弃牌
                            discarded_card = current.hand.pop(idx)
                            current.discard.append(discarded_card)
                            print(f"{current.name} 弃掉了 {discarded_card.name}")
                        else:
                            print("编号无效，请重新选择。")
                    except ValueError:
                        print("请输入数字编号。")

            turn += 1
            continue

        # 更新基础行动力（基于当前HP）
        current._base_actions = max(2, current.hp // 2)

        # 本回合行动次数
        actions_remaining = current.actions

        # 当还有行动力时，可以继续出牌
        while actions_remaining > 0:
            print(f"\n剩余行动力: {current.actions}")
            print(f"{current.name} 手牌: {[f'{i}:{c.name}' for i,c in enumerate(current.hand)]}")

            # 如果没有手牌，自动抽一张并结束回合
            if not current.hand:
                print("没有手牌，自动抽一张牌")
                current.draw(1)
                actions_remaining = 0  # 用掉所有行动力
                break

            # 提供选项：出牌、结束回合或投降
            choice = input(f"选择要使用的卡牌编号(0-{len(current.hand)-1})，输入-1结束回合，输入-2投降: ").strip()

            if choice == "-1":
                print("选择结束回合")
                break
            elif choice == "-2":
                print(f"{current.name} 选择投降！")
                print(f"{enemy.name} 获胜！")
                input("按回车返回主菜单...")
                return

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

        # 弃牌环节
        # 计算玩家最多可以保留的牌数（行动力上限，最小为2）
        max_cards = max(2, current._base_actions)

        # 如果手牌数量超过最大保留数量，进入弃牌环节
        if len(current.hand) > max_cards:
            print(f"\n===== 弃牌环节 =====")
            print(f"{current.name} 手牌数量({len(current.hand)})超过最大保留数量({max_cards})，需要弃牌")

            # 不断弃牌直到手牌数量不超过最大保留数量
            while len(current.hand) > max_cards:
                print(f"\n{current.name} 手牌: {[f'{i}:{c.name}' for i,c in enumerate(current.hand)]}")
                print(f"需要弃掉 {len(current.hand) - max_cards} 张牌")

                try:
                    choice = input(f"选择要弃掉的卡牌编号(0-{len(current.hand)-1}): ").strip()
                    idx = int(choice)

                    if 0 <= idx < len(current.hand):
                        # 弃牌
                        discarded_card = current.hand.pop(idx)
                        current.discard.append(discarded_card)
                        print(f"{current.name} 弃掉了 {discarded_card.name}")
                    else:
                        print("编号无效，请重新选择。")
                except ValueError:
                    print("请输入数字编号。")

        turn += 1



# ====== 主菜单 ======
def main_menu():
    while True:
        print("\n===== 欢迎来到卡牌游戏 =====")
        print("1. 开始新游戏（默认牌堆大小 12）")
        print("2. 开始新游戏（自定义牌堆大小）")
        print("3. 开始新游戏（开启调试卡牌）")
        print("4. 退出游戏")
        choice = input("请选择操作 (1/2/3/4): ").strip()

        if choice == "1":
            game_demo(deck_size=DEFAULT_DECK_SIZE, debug_mode=False)
        elif choice == "2":
            try:
                n = int(input("输入每副牌的目标牌数（建议 8-30）: ").strip())
                n = max(4, min(60, n))
                debug_choice = input("是否开启调试卡牌？(y/n): ").strip().lower()
                debug_mode = debug_choice == 'y'
                game_demo(deck_size=n, debug_mode=debug_mode)
            except ValueError:
                print("输入无效，返回菜单。")
        elif choice == "3":
            game_demo(deck_size=DEFAULT_DECK_SIZE, debug_mode=True)
        elif choice == "4":
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
# [更新3] 新增 build_deck_from_prototypes 函数：根据信赖度 (100 - rarity) 计算权重，并按期望值分配每种卡在牌堆中的副本数（目标牌堆大小可配置，默认为 12）
# [更新4] 将原先的 deck_template 改为 deck_prototypes（每种卡只定义一次并包含 rarity）
# [更新5] Player 初始化现在接收已经构建好的牌堆（每局会为双方单独构建）
# [更新6] 在主菜单加入"自定义牌堆大小"选项，方便调试稀有度效果
# [更新7] 保留了之前所有功能：交互闪现骰子、回合信息/效果显示、跳过回合逻辑、胜负后返回主菜单等
# [更新8] 增加负行动力机制：出牌前减去负行动力，可以跳过多个回合
# [更新9] 新增曼妥思之神卡牌（双判定回血/回SAN）
# [更新10] 新增300龟机制杀卡牌（骰到300可强制扣除对方数值）
# [更新11] 修复加速药的作用，时期能增加对方骰子的速度而不是己方的

# v1.2.1
# [更新1] 暂时移除了谬误稻草人
# [更新2] 新增控制血量和san变化的中间变量, 方便后续如谬误稻草人一类卡牌功能的实现
# [更新3] 调整了更清晰的状态改变显示
# [更新4] 新增卡牌声明时骰子最小点数的变量
# [更新5] 新增赛前掷骰子决定先手环节

# v1.3.0
# [更新1] 修复了曼妥思之神的双重判定问题
# [更新2] 新增了可以指定点数的调试卡牌
# [更新3] 优化300龟,300龟可以正常实现功能
# [更新4] 新增暮光巫蜥卡牌
# [更新5] 优化初始界面,现在可以选择是否在牌堆中加入调试卡牌
# [更新6] 新增投降功能

# v1.3.1
# [更新1] 新增弃牌环节，当玩家出牌回合结束或行动力不足时，玩家需要弃牌,玩家最多只能保存数值等于行动力上限张牌，最小值为2
# [更新2] 新增卡牌鸡机
# [更新3] 新增卡牌眼镜蛙
