import json

from sessions import session, save_session
from get_game_config import get_game_config, get_level_from_xp, get_name_from_item_id, get_attribute_from_mission_id, get_xp_from_level, get_attribute_from_item_id, get_item_from_subcat_functional
from constants import Constant
from engine import apply_cost, apply_collect, apply_collect_xp, timestamp_now

def get_strategy_type(id):
    if id == 8:
        return "Defensive"
    if id == 9:
        return "Mid Defensive"
    if id == 7:
        return "Mid Aggressive"
    if id == 10:
        return "Aggressive"
    return "Unknown Strategy"

def command(USERID, data):
    timestamp = data["ts"]
    first_number = data["first_number"]
    accessToken = data["accessToken"]
    tries = data["tries"]
    publishActions = data["publishActions"]
    commands = data["commands"]
    
    for i, comm in enumerate(commands):
        cmd = comm["cmd"]
        args = comm["args"]
        do_command(USERID, cmd, args)
    save_session(USERID) # Save session

def do_command(USERID, cmd, args):
    save = session(USERID)
    print (" [+] COMMAND: ", cmd, "(", args, ") -> ", sep='', end='')

    if cmd == Constant.CMD_GAME_STATUS:
        print(" ".join(args))

    elif cmd == Constant.CMD_BUY:
        id = args[0]
        x = args[1]
        y = args[2]
        frame = args[3] # TODO ??
        town_id = args[4]
        bool_dont_modify_resources = bool(args[5]) # 1 if the game "buys" for you, so does not substract whatever the item cost is.
        price_multiplier = args[6]
        type = args[7]
        print("Add", str(get_name_from_item_id(id)), "at", f"({x},{y})")
        collected_at_timestamp = timestamp_now()
        level = 0 # TODO 
        orientation = 0
        map = save["maps"][town_id]
        if not bool_dont_modify_resources:
            apply_cost(save["playerInfo"], map, id, price_multiplier)
            xp = int(get_attribute_from_item_id(id, "xp"))
            map["xp"] = map["xp"] + xp
        map["items"] += [[id, x, y, orientation, collected_at_timestamp, level]]
    
    elif cmd == Constant.CMD_COMPLETE_TUTORIAL:
        tutorial_step = args[0]
        print("Tutorial step", tutorial_step, "reached.")
        if tutorial_step >= 31: # 31 is Dragon choosing. After that, you have some freedom. There's at least until step 45.
            print("Tutorial COMPLETED!")
            save["playerInfo"]["completed_tutorial"] = 1
            save["privateState"]["dragonNestActive"] = 1 
    
    elif cmd == Constant.CMD_MOVE:
        ix = args[0]
        iy = args[1]
        id = args[2]
        newx = args[3]
        newy = args[4]
        frame = args[5]
        town_id = args[6]
        reason = args[7] # "Unitat", "moveTo", "colisio", "MouseUsed"
        print("Move", str(get_name_from_item_id(id)), "from", f"({ix},{iy})", "to", f"({newx},{newy})")
        map = save["maps"][town_id]
        for item in map["items"]:
            if item[0] == id and item[1] == ix and item[2] == iy:
                item[1] = newx
                item[2] = newy
                break
    
    elif cmd == Constant.CMD_COLLECT:
        x = args[0]
        y = args[1]
        town_id = args[2]
        id = args[3]
        num_units_contained_when_harvested = args[4]#TODO does this affect multiplier?
        resource_multiplier = args[5]
        cash_to_substract = args[6]
        print("Collect", str(get_name_from_item_id(id)))
        map = save["maps"][town_id]
        apply_collect(save["playerInfo"], map, id, resource_multiplier)
        save["playerInfo"]["cash"] = max(save["playerInfo"]["cash"] - cash_to_substract, 0)
    
    elif cmd == Constant.CMD_SELL:
        x = args[0]
        y = args[1]
        id = args[2]
        town_id = args[3]
        bool_dont_modify_resources = args[4]
        reason = args[5]
        print("Remove", str(get_name_from_item_id(id)), "from", f"({x},{y}). Reason: {reason}")
        map = save["maps"][town_id]
        for item in map["items"]:
            if item[0] == id and item[1] == x and item[2] == y:
                map["items"].remove(item)
                break
        if not bool_dont_modify_resources:
            price_multiplier = -0.05
            if get_attribute_from_item_id(id, "cost_type") != "c":
                apply_cost(save["playerInfo"], save["maps"][town_id], id, price_multiplier)
        if reason == 'KILL':
            # Add to graveyard for potential resurrection
            if "graveyard" not in save["privateState"]:
                save["privateState"]["graveyard"] = []
            
            # Capacity limit (original game had 20 slots)
            MAX_GRAVEYARD = 20
            if len(save["privateState"]["graveyard"]) >= MAX_GRAVEYARD:
                # Remove oldest entry
                save["privateState"]["graveyard"].pop(0)
                print(f"  -> Graveyard full, removed oldest entry")
            
            # Add entry with 48-hour expiration
            graveyard_entry = {
                "unit_id": id,
                "timestamp": timestamp_now(),
                "expires_at": timestamp_now() + (48 * 3600),  # 48 hours
                "town_id": town_id
            }
            save["privateState"]["graveyard"].append(graveyard_entry)
            print(f"  -> Added to graveyard (expires in 48 hours)")
        
        if reason == 'SQEST':
            # Track units entering quest for later survivor/death processing
            if "quest_units" not in save["privateState"]:
                save["privateState"]["quest_units"] = []
            save["privateState"]["quest_units"].append({
                "unit_id": id,
                "x": x,
                "y": y,
                "town_id": town_id
            })
            print(f"  -> Unit entered quest (SQEST tracking)")
    
    elif cmd == Constant.CMD_KILL:
        x = args[0]
        y = args[1]
        id = args[2]
        town_id = args[3]
        type = args[4]
        print("Kill", str(get_name_from_item_id(id)), "from", f"({x},{y}).")
        map = save["maps"][town_id]
        for item in map["items"]:
            if item[0] == id and item[1] == x and item[2] == y:
                apply_collect_xp(map, id)
                map["items"].remove(item)
                break
    
    elif cmd == Constant.CMD_COMPLETE_MISSION:
        mission_id = args[0]
        skipped_with_cash = bool(args[1])
        print("Complete mission", mission_id, ":", str(get_attribute_from_mission_id(mission_id, "title")))
        if skipped_with_cash:
            # Get skip cost from mission config (default to 5 cash if not specified)
            skip_cost = get_attribute_from_mission_id(mission_id, "skip_cost")
            cash_to_substract = int(skip_cost) if skip_cost else 5
            save["playerInfo"]["cash"] = max(save["playerInfo"]["cash"] - cash_to_substract, 0)
        save["privateState"]["completedMissions"] += [mission_id]
    
    elif cmd == Constant.CMD_REWARD_MISSION:
        town_id = args[0]
        mission_id = args[1]
        print("Reward mission", mission_id, ":", str(get_attribute_from_mission_id(mission_id, "title")))
        reward = int(get_attribute_from_mission_id(mission_id, "reward")) # gold
        save["maps"][town_id]["coins"] += reward   
        save["privateState"]["rewardedMissions"] += [mission_id]
    
    elif cmd == Constant.CMD_PUSH_UNIT:
        unit_x = args[0]
        unit_y = args[1]
        unit_id = args[2]
        b_x = args[3]
        b_y = args[4]
        town_id = args[5]
        print("Push", str(get_name_from_item_id(unit_id)), "to", f"({b_x},{b_y}).")
        map = save["maps"][town_id]
        # Unit into building
        for item in map["items"]:
            if item[1] == b_x and item[2] == b_y:
                if len(item) < 7:
                    item += [[]]
                item[6] += [unit_id]
                break
        # Remove unit
        for item in map["items"]:
            if item[0] == unit_id and item[1] == unit_x and item[2] == unit_y:
                map["items"].remove(item)
                break
    
    elif cmd == Constant.CMD_POP_UNIT:
        b_x = args[0]
        b_y = args[1]
        town_id = args[2]
        unit_id = args[3]
        place_popped_unit = len(args) > 4
        if place_popped_unit:
            unit_x = args[4]
            unit_y = args[5]
            unit_frame = args[6] # unknown use
        print("Pop", str(get_name_from_item_id(unit_id)), "from", f"({b_x},{b_y}).")
        map = save["maps"][town_id]
        # Remove unit from building
        for item in map["items"]:
            if item[1] == b_x and item[2] == b_y:
                if len(item) < 7:
                    break
                item[6].remove(unit_id)
                break
        if place_popped_unit:
            # Spawn unit outside
            collected_at_timestamp = timestamp_now()
            level = 0 # TODO 
            orientation = 0
            map["items"] += [[unit_id, unit_x, unit_y, orientation, collected_at_timestamp, level]]
    
    elif cmd == Constant.CMD_RT_LEVEL_UP:
        new_level = args[0]
        print("Level Up!:", new_level)
        map = save["maps"][0] # TODO : xp must be general, since theres no given town_id
        map["level"] = args[0]
        current_xp = map["xp"]
        min_expected_xp = get_xp_from_level(max(0, new_level - 1))
        map["xp"] = max(min_expected_xp, current_xp) # try to fix problems with not counting XP... by keeping up with client-side level counting

    elif cmd == Constant.CMD_RT_PUBLISH_SCORE:
        new_xp = args[0]
        print("xp set to", new_xp)
        map = save["maps"][0] # TODO : xp must be general, since theres no given town_id
        map["xp"] = new_xp
        map["level"] = get_level_from_xp(new_xp)

    elif cmd == Constant.CMD_EXPAND:
        land_id = args[0]
        resource = args[1]
        town_id = int(args[2])
        print("Expansion", land_id, "purchased")
        map = save["maps"][town_id]
        if land_id in map["expansions"]:
            return
        # Substract resources
        expansion_prices = get_game_config()["expansion_prices"]
        exp = expansion_prices[len(map["expansions"]) - 1]
        if resource == "gold":
            to_substract = exp["coins"]
            save["maps"][town_id]["coins"] = max(save["maps"][town_id]["coins"] - to_substract, 0)
        elif resource == "cash":
            to_substract = exp["cash"]
            save["playerInfo"]["cash"] = max(save["playerInfo"]["cash"] - to_substract, 0)
        # Add expansion
        map["expansions"].append(land_id)

    elif cmd == Constant.CMD_NAME_MAP:
        town_id =int(args[0])
        new_name = args[1]
        print(f"Map name changed to '{new_name}'.")
        save["playerInfo"]["map_names"][town_id] = new_name

    elif cmd == Constant.CMD_EXCHANGE_CASH:
        town_id = args[0]
        print("Exchange cash -> coins.")
        save["playerInfo"]["cash"] = max(save["playerInfo"]["cash"] - 5, 0)#maybe make function for editing resources
        save["maps"][town_id]["coins"] += 2500

    elif cmd == Constant.CMD_STORE_ITEM:
        x = args[0]
        y = args[1]
        town_id = int(args[2])
        item_id = args[3]
        print("Store", str(get_name_from_item_id(item_id)), "from", f"({x},{y})")
        map = save["maps"][town_id]
        for item in map["items"]:
            if item[0] == item_id and item[1] == x and item[2] == y:
                map["items"].remove(item)
                break
        length = len(save["privateState"]["gifts"])
        if length <= item_id:
            for i in range(item_id - length + 1):
                save["privateState"]["gifts"].append(0)
        save["privateState"]["gifts"][item_id] += 1

    elif cmd == Constant.CMD_PLACE_GIFT:
        item_id = args[0]
        x = args[1]
        y = args[2]
        town_id = args[3]#unsure, both 3 and 4 seem to stay 0
        args[4]#unknown yet
        print("Add", str(get_name_from_item_id(item_id)), "at", f"({x},{y})")
        items = save["maps"][town_id]["items"]
        orientation = 0#TODO
        collected_at_timestamp = timestamp_now()
        level = 0
        items += [[item_id, x, y, orientation, collected_at_timestamp, level]]#maybe make function for adding items
        save["privateState"]["gifts"][item_id] -= 1
        if save["privateState"]["gifts"][item_id] == 0: #removes excess zeros at end if necessary
            while(save["privateState"]["gifts"][-1] == 0):
                save["privateState"]["gifts"].pop()  

    elif cmd == Constant.CMD_SELL_GIFT:
        item_id = args[0]
        town_id = args[1]
        print("Gift", str(get_name_from_item_id(item_id)), "sold on town:",town_id)
        gifts = save["privateState"]["gifts"]
        gifts[item_id] -= 1
        if gifts[item_id] == 0: #removes excess zeros at end if necessary
            while(len(gifts) != 0 and gifts[-1] == 0):
                gifts.pop()
        price_multiplier = -0.05
        if get_attribute_from_item_id(item_id, "cost_type") != "c":
            apply_cost(save["playerInfo"], save["maps"][town_id], item_id, price_multiplier)
    
    elif cmd == Constant.CMD_ACTIVATE_DRAGON:
        currency = args[0]
        print("Dragon nest activated.")
        if currency == 'c':
            save["playerInfo"]["cash"] = max(int(save["playerInfo"]["cash"] - 50), 0)
        elif currency == 'g':
            map = save["maps"]
            map[0]["coins"] = max(int(map[0]["coins"] - 100000), 0)
        save["privateState"]["dragonNestActive"] = 1
        save["privateState"]["timeStampTakeCare"] = -1 # remove timer if any
    
    elif cmd == Constant.CMD_DESACTIVATE_DRAGON:
        print("Dragon nest deactivated.")
        pState = save["privateState"]
        pState["dragonNestActive"] = 0
        # reset step and dragon numbers
        pState["stepNumber"] = 0
        pState["dragonNumber"] = 0
        pState["timeStampTakeCare"] = -1 # remove timer if any

    elif cmd == Constant.CMD_NEXT_DRAGON_STEP:
        unknown = args[0]
        print("Dragon step increased.")
        pState = save["privateState"]
        pState["stepNumber"] += 1
        pState["timeStampTakeCare"] = timestamp_now()

    elif cmd == Constant.CMD_NEXT_DRAGON:
        print("Dragon step reset and dragonNumber increased.")
        pState = save["privateState"]
        pState["stepNumber"] = 0
        pState["dragonNumber"] += 1
        pState["timeStampTakeCare"] = -1 # remove timer

    elif cmd == Constant.CMD_DRAGON_BUY_STEP_CASH:
        price = args[0]
        print("Buy dragon step with cash.")
        save["playerInfo"]["cash"] = max(int(save["playerInfo"]["cash"] - price), 0)
        save["privateState"]["timeStampTakeCare"] = -1 # remove timer

    elif cmd == Constant.CMD_RIDER_BUY_STEP_CASH:
        price = args[0]
        print("Buy rider step with cash.")
        save["playerInfo"]["cash"] = max(int(save["playerInfo"]["cash"] - price), 0)
        save["privateState"]["riderTimeStamp"] = -1 # remove timer

    elif cmd == Constant.CMD_NEXT_RIDER_STEP:
        print("Rider step increased.")
        pState = save["privateState"]
        pState["riderStepNumber"] += 1
        pState["riderTimeStamp"] = timestamp_now()
    
    elif cmd == Constant.CMD_SELECT_RIDER:
        number = int(args[0])
        pState = save["privateState"]
        if number == 1 or number == 2 or number == 3:
            pState["riderNumber"] = number
            print("Rider", number, "Selected.")
        else:
            pState["riderNumber"] = 0
            pState["riderStepNumber"] = 0
            pState["riderTimeStamp"] = -1 # remove timer
            print("Rider reset.")
    
    elif cmd == Constant.CMD_ORIENT:
        x = args[0]
        y = args[1]
        new_orientation = args[2]
        town_id = args[3]
        print("Item at", f"({x},{y})", "changed to orientation", new_orientation)
        map = save["maps"][town_id]
        for item in map["items"]:
            if item[1] == x and item[2] == y:
                item[3] = new_orientation
                break
    
    elif cmd == Constant.CMD_MONSTER_BUY_STEP_CASH:
        price = args[0]
        print("Buy monster step with cash.")
        save["playerInfo"]["cash"] = max(int(save["playerInfo"]["cash"] - price), 0)
        save["privateState"]["timeStampTakeCareMonster"] = -1 # remove timer
    
    elif cmd == Constant.CMD_ACTIVATE_MONSTER:
        currency = args[0]
        print("Monster nest activated.")
        if currency == 'c':
            save["playerInfo"]["cash"] = max(int(save["playerInfo"]["cash"] - 50), 0)
        elif currency == 'g':
            map = save["maps"]
            map[0]["coins"] = max(int(map[0]["coins"] - 100000), 0)
        save["privateState"]["monsterNestActive"] = 1
        save["privateState"]["timeStampTakeCareMonster"] = -1 # remove timer if any
    
    elif cmd == Constant.CMD_DESACTIVATE_MONSTER: # cmd called too late
        print("Monster nest deactivated.")
        pState = save["privateState"]
        pState["monsterNestActive"] = 0
        pState["stepMonsterNumber"] = 0
        pState["MonsterNumber"] = 0
        pState["timeStampTakeCareMonster"] = -1 # remove timer if any


    elif cmd == Constant.CMD_NEXT_MONSTER_STEP:
        print("Monster Step increased.")
        pState = save["privateState"]
        pState["stepMonsterNumber"] += 1
        pState["timeStampTakeCareMonster"] = timestamp_now()

    elif cmd == Constant.CMD_NEXT_MONSTER:
        print("Monster Step reset and Monster Number increased.")
        pState = save["privateState"]
        pState["stepMonsterNumber"] = 0
        pState["monsterNumber"] += 1
        pState["timeStampTakeCareMonster"] = -1 # remove timer

    elif cmd == Constant.CMD_WIN_BONUS:
        coins = args[0]
        town_id = args[1]
        hero = args[2]
        claimId = args[3]
        cash = args[4]

        print("Claiming Win Bonus")
        map = save["maps"][town_id]

        if cash != 0:
            save["playerInfo"]["cash"] = save["playerInfo"]["cash"] + cash
            print("Added " + str(cash) + " Cash to players balance")

        if coins != 0:
            map["coins"] = map["coins"] + coins
            print("Added " + str(coins) + " Gold to players balance")

        if hero != 0:
            length = len(save["privateState"]["gifts"])
            if length <= hero:
                for i in range(hero - length + 1):
                    save["privateState"]["gifts"].append(0)
            save["privateState"]["gifts"][hero] += 1
            print("Added Hero ID=" + str(hero))

        pState = save["privateState"]
        pState["bonusNextId"] = claimId + 1
        pState["timestampLastBonus"] = timestamp_now()

    elif cmd == Constant.CMD_ADMIN_ADD_ANIMAL:
        subcatFunc = str(args[0])
        toBeAdded = int(args[1])
        print("Added", toBeAdded, get_item_from_subcat_functional(subcatFunc)["name"])

        # TODO
        oAnimals: dict = save["privateState"]["arrayAnimals"]
        oAnimals[subcatFunc] = toBeAdded + (oAnimals[subcatFunc] if subcatFunc in oAnimals else 0)
    
    elif cmd == Constant.CMD_GRAVEYARD_BUY_POTIONS:
        # no args
        print("Graveyard buy potion")
        # info from config
        graveyard_potions = get_game_config()["globals"]["GRAVEYARD_POTIONS"]
        amount = graveyard_potions["amount"]
        price_cash = graveyard_potions["price"]["c"]
        # pay
        save["playerInfo"]["cash"] = max(int(save["playerInfo"]["cash"] - price_cash), 0)
        # add potion
        save["privateState"]["potion"] += amount

    elif cmd == Constant.CMD_PUT_GRAVEYARD:
        unit_id = args[0]
        town_id = args[1] if len(args) > 1 else 0
        print(f"Put unit {get_name_from_item_id(unit_id)} (ID: {unit_id}) into graveyard")
        
        # Initialize graveyard if needed
        if "graveyard" not in save["privateState"]:
            save["privateState"]["graveyard"] = []
        
        # Capacity limit (original game had 20 slots)
        MAX_GRAVEYARD = 20
        if len(save["privateState"]["graveyard"]) >= MAX_GRAVEYARD:
            # Remove oldest entry
            save["privateState"]["graveyard"].pop(0)
            print("  -> Graveyard full, removed oldest")
        
        # Add to graveyard with 48-hour expiration
        graveyard_entry = {
            "unit_id": unit_id,
            "timestamp": timestamp_now(),
            "expires_at": timestamp_now() + (48 * 3600),  # 48 hours
            "town_id": town_id
        }
        save["privateState"]["graveyard"].append(graveyard_entry)
        print(f"  -> Added to graveyard (expires in 48 hours)")

    elif cmd == Constant.CMD_RESURRECT_HERO:
        unit_id = args[0]
        x = args[1]
        y = args[2]
        town_id = args[3]
        bool_used_potion = len(args) > 4 and args[4] == '1'
        print("Resurrect", str(get_name_from_item_id(unit_id)), "from graveyard")
        # pay
        if bool_used_potion:
            quantity = 1
            save["privateState"]["potion"] = max(int(save["privateState"]["potion"] - quantity), 0)
        else:
            # Pay with cash - cost based on unit strength (default 10 cash)
            unit_life = get_attribute_from_item_id(unit_id, "life")
            resurrection_cost = max(5, int(unit_life) // 100) if unit_life else 10
            save["playerInfo"]["cash"] = max(save["playerInfo"]["cash"] - resurrection_cost, 0)
        # Place unit
        collected_at_timestamp = timestamp_now()
        level = 0
        orientation = 0
        map = save["maps"][town_id]
        map["items"] += [[unit_id, x, y, orientation, collected_at_timestamp, level]]

    elif cmd == Constant.CMD_BUY_SUPER_OFFER_PACK:
        town_id = args[0]
        unknown2 = args[1] # this is probably the super offer pack ID?
        items = args[2]
        cash_used = args[3]
        
        map = save["maps"][town_id]

        item_array = items.split(',')
        for item in item_array:
            item_id = int(item)
            length = len(save["privateState"]["gifts"])
            if length <= item_id:
                for i in range(item_id - length + 1):
                    save["privateState"]["gifts"].append(0)
            save["privateState"]["gifts"][item_id] += 1

        save["playerInfo"]["cash"] = max(save["playerInfo"]["cash"] - cash_used, 0)#maybe make function for editing resources
        print(f"Used {cash_used} cash to buy super offer pack!")

    elif cmd == Constant.CMD_SET_STRATEGY:
        strategy_type = args[0]
        type_name = get_strategy_type(strategy_type)
        save["privateState"]["strategy"] = strategy_type
        print(f"Set defense strategy type to {type_name}")

    elif cmd == Constant.CMD_START_QUEST:
        quest_id = args[0]
        town_id = args[1]
        print(f"Start quest {quest_id}")

    elif cmd == Constant.CMD_END_QUEST:
        data = json.loads(args[0])
        town_id = data["map"]
        gold_gained = data["resources"]["g"]
        xp_gained = data["resources"]["x"]
        units = data["units"]  # List of surviving unit IDs
        win = data["win"] == 1
        duration_sec = data["duration"]
        voluntary_end = data["voluntary_end"] == 1
        quest_id = int(data["quest_id"])
        item_rewards = data["item_rewards"] if "item_rewards" in data else None
        activators_left = data["activators_left"] if "activators_left" in data else None
        difficulty = int(data["difficulty"])  # 1, 2, or 3 stars

        # Always award resources (even on loss you get some)
        save["maps"][town_id]["coins"] += int(gold_gained)
        save["maps"][town_id]["xp"] += int(xp_gained)

        # Only process win results
        if win and not voluntary_end:
            # Update quest rank (stars) - difficulty is which star level (1, 2, or 3)
            quest_key = str(quest_id)
            if "questsRank" not in save["privateState"]:
                save["privateState"]["questsRank"] = {}
            
            current_rank = save["privateState"]["questsRank"].get(quest_key, 0)
            # Only update if this difficulty is higher than current
            if difficulty > current_rank:
                save["privateState"]["questsRank"][quest_key] = difficulty
                print(f"  -> Awarded {difficulty} star(s) for quest {quest_id}!")
            
            # Unlock next quest
            save["privateState"]["unlockedQuestIndex"] = max(quest_id + 1, save["privateState"].get("unlockedQuestIndex", 0))
            
            # Track quest times using dictionary (NOT array - quest IDs are huge like 100000006)
            quest_key = str(quest_id)
            quest_times = save["maps"][town_id].get("questTimes", {})
            last_quest_times = save["maps"][town_id].get("lastQuestTimes", {})
            
            # Convert old array format to dict if needed
            if isinstance(quest_times, list):
                quest_times = {}
            if isinstance(last_quest_times, list):
                last_quest_times = {}
            
            # Update with best/last times
            current_best = quest_times.get(quest_key, 999999)
            quest_times[quest_key] = min(current_best, duration_sec)
            last_quest_times[quest_key] = duration_sec
            
            save["maps"][town_id]["questTimes"] = quest_times
            save["maps"][town_id]["lastQuestTimes"] = last_quest_times
            
            print(f"Quest {quest_id} WON at difficulty {difficulty}! Duration: {duration_sec}s")
        else:
            if voluntary_end:
                print(f"Quest {quest_id} voluntarily ended (no rewards)")
            else:
                print(f"Quest {quest_id} LOST")
        
        # Process quest units - survivors return, dead go to graveyard
        quest_units = save["privateState"].get("quest_units", [])
        if quest_units:
            # Parse survivor unit IDs from the data
            survivor_ids = set()
            for u in units:
                if isinstance(u, dict):
                    survivor_ids.add(u.get("id", u.get("unit_id")))
                else:
                    survivor_ids.add(int(u) if isinstance(u, str) else u)
            
            # Process each unit that entered the quest
            map_items = save["maps"][town_id]["items"]
            survivors_returned = 0
            units_died = 0
            
            for quest_unit in quest_units:
                unit_id = quest_unit["unit_id"]
                if unit_id in survivor_ids:
                    # Survived - add back to map
                    map_items.append([
                        unit_id, 
                        quest_unit["x"], 
                        quest_unit["y"], 
                        0,  # orientation
                        timestamp_now(), 
                        0   # level
                    ])
                    survivors_returned += 1
                else:
                    # Died - add to graveyard
                    if "graveyard" not in save["privateState"]:
                        save["privateState"]["graveyard"] = []
                    
                    MAX_GRAVEYARD = 20
                    if len(save["privateState"]["graveyard"]) >= MAX_GRAVEYARD:
                        save["privateState"]["graveyard"].pop(0)
                    
                    save["privateState"]["graveyard"].append({
                        "unit_id": unit_id,
                        "timestamp": timestamp_now(),
                        "expires_at": timestamp_now() + (48 * 3600),
                        "town_id": town_id
                    })
                    units_died += 1
            
            print(f"  -> Quest units: {survivors_returned} returned, {units_died} died")
            
            # Clear tracked quest units
            save["privateState"]["quest_units"] = []

    elif cmd == Constant.CMD_ADD_COLLECTABLE:
        collection_id = args[0]
        collectible_id = args[1]
        print(f"Add collectable {collectible_id} to collection {collection_id}")
        pState = save["privateState"]
        if "collectables" not in pState:
            pState["collectables"] = {}
        collection_key = str(collection_id)
        if collection_key not in pState["collectables"]:
            pState["collectables"][collection_key] = []
        if collectible_id not in pState["collectables"][collection_key]:
            pState["collectables"][collection_key].append(collectible_id)

    else:
        print(f"Unhandled command '{cmd}' -> args", args)
        return
    
