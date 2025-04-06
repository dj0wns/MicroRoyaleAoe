import click
import math

from AoE2ScenarioParser.scenarios.aoe2_de_scenario import AoE2DEScenario
from AoE2ScenarioParser.datasets.other import OtherInfo
from AoE2ScenarioParser.datasets.units import UnitInfo
from AoE2ScenarioParser.datasets.techs import TechInfo
from AoE2ScenarioParser.datasets.trigger_lists import Attribute

@click.command()
@click.option('--base-map', type=click.Path(exists=True))
@click.option('--out-file', type=click.Path(exists=False))
@click.option('--map-size', type=int, default=0)
@click.option('--player-count', type=int)
@click.option('--storm-seconds', type=int)
@click.option('--damage-frequency-in-seconds', type=int)
@click.option('--damage-amount', type=int)
@click.option('--block-size', type=int, help='The size of each trigger area, 1 means its a 1x1 tile, 3 means a 3x3 tile, this helps reduce trigger count (and stability) at larger map sizes but makes the circle less smooth)')
@click.option('--unit-to-generate', type=str, help='[MULTIPLE] Fully qualified name of the unit in the AoEScenarioParser (https://ksneijders.github.io/AoE2ScenarioParser/api_docs/datasets/units/) that we want to generate, if blank will not add any units. These units will be divided evenly in a circle about the center of the map per player. Example: For crossbow you would put: UnitInfo.CROSSBOWMAN.ID', multiple=True)
@click.option('--unit-count', type=int, help='[MULTIPLE] Number of that unit to generate', multiple=True)
@click.option('--tech-to-provide', type=str, multiple=True, help='[MULTIPLE] Techs that will be researched by every player, use the fully qualified name in the AoEScenarioParser (https://ksneijders.github.io/AoE2ScenarioParser/api_docs/datasets/techs/). Example: TechInfo.FLETCHING.ID')
@click.option('--tech-reward', type=str, multiple=True, help='[MULTIPLE] Techs that will be researched by every player after meeting a kill goal. (https://ksneijders.github.io/AoE2ScenarioParser/api_docs/datasets/techs/). Example: TechInfo.FLETCHING.ID')
@click.option('--tech-reward-kill-amount', type=int, multiple=True, help='[MULTIPLE] The kill goal for the corresponding reward tech.')
def main(
    base_map,
    out_file,
    map_size,
    player_count,
    storm_seconds,
    damage_frequency_in_seconds,
    damage_amount,
    block_size,
    unit_to_generate = [],
    unit_count = [],
    tech_to_provide = [],
    tech_reward = [],
    tech_reward_kill_amount = []):

  scenario = AoE2DEScenario.from_file(base_map)

  set_up_players(scenario.player_manager, player_count)

  map_manager = scenario.map_manager
  if map_size:
    map_manager.map_size = map_size
  else:
    map_size = map_manager.map_size

  if unit_to_generate:
    generate_units(scenario.unit_manager,
        player_count,
        map_size,
        unit_to_generate,
        unit_count)

  trigger_manager = scenario.trigger_manager

  if tech_to_provide:
    add_initial_tech_triggers(trigger_manager,
      player_count,
      tech_to_provide)

  if tech_reward:
    add_reward_triggers(trigger_manager,
      player_count,
      tech_reward,
      tech_reward_kill_amount)

  add_perimeter_triggers(
      trigger_manager,
      map_size,
      player_count,
      storm_seconds,
      damage_frequency_in_seconds,
      damage_amount,
      block_size)

  scenario.write_to_file(out_file)

def set_up_players(
    player_manager,
    player_count):
  player_manager.active_players = player_count

def add_reward_triggers(trigger_manager,
    player_count,
    tech_reward,
    tech_reward_kill_amount):
  for p in range(player_count):
    for i in range(len(tech_reward)):
      reward_trigger = trigger_manager.add_trigger(
          f'{p}_{i}_reward_trigger', looping=False)
      reward_trigger.new_condition.accumulate_attribute(
          source_player=p+1, #gaia is 0, so 1 indexed
          quantity=tech_reward_kill_amount[i],
          attribute=Attribute.UNITS_KILLED)
      reward_trigger.new_effect.research_technology(
          source_player=p+1, #gaia is 0, so 1 indexed
          technology=eval(tech_reward[i]),
          force_research_technology=1)
      # Send message to all players that Player p has researched a tech!
      for p_i in range(player_count):
        reward_trigger.new_effect.send_chat(
            source_player=p_i + 1, #gaia is 0, so 1 indexed
            message=f"Player {p+1} has researched {tech_reward[i].split('.')[1]}")

def add_initial_tech_triggers(
    trigger_manager,
    player_count,
    tech_to_provide):
  for p in range(player_count):
    init_trigger = trigger_manager.add_trigger(
          f'{p}_init_trigger', looping=False)
    for tech in tech_to_provide:
      init_trigger.new_effect.research_technology(
          source_player=p+1, #gaia is 0, so 1 indexed
          technology=eval(tech),
          force_research_technology=1)

def generate_units(
    unit_manager,
    player_count,
    map_size,
    unit_to_generate,
    unit_count):
  row_length = 10
  # Calculate the spawn circle
  spawn_radius = map_size/2. * 0.7
  spawn_angle = 2. * math.pi / float(player_count)

  for p in range(player_count):
    units_per_row = 10
    row_count = 0
    col_count = 0
    initial_x = map_size/2. + math.sin(spawn_angle * float(p)) * spawn_radius
    initial_y = map_size/2. + math.cos(spawn_angle * float(p)) * spawn_radius
    distance_increment = 0.5 #half tile per unit

    unit_index = 0
    for unit_index in range(len(unit_to_generate)):
      for i in range(unit_count[unit_index]):
        unit_manager.add_unit(p + 1, #gaia is 0, so 1 indexed here
            unit_const = eval(unit_to_generate[unit_index]),
            x = initial_x + row_count * distance_increment,
            y = initial_y + col_count * distance_increment,
            rotation = math.degrees((spawn_angle * float(p))))
        row_count += 1
        if row_count == units_per_row:
          row_count = 0
          col_count += 1

def add_perimeter_triggers(
    trigger_manager,
    map_size,
    player_count,
    storm_seconds,
    damage_frequency_in_seconds,
    damage_amount,
    block_size):
  max_distance = math.sqrt(pow(map_size/2., 2.) + pow(map_size/2., 2.))
  time_per_distance = storm_seconds / max_distance
  for x in range(0, map_size, block_size):
    for y in range(0, map_size, block_size):
      added_width = block_size - 1
      # get center of each block
      delta_x = abs(map_size/2. - (x + x + added_width)/2.)
      delta_y = abs(map_size/2. - (y+y+added_width)/2.)
      # use distance from center to calculate
      distance = math.sqrt(pow(delta_x, 2.) + pow(delta_y, 2.))
      time_to_storm = (max_distance - distance) * time_per_distance
      storm_trigger = trigger_manager.add_trigger(
          f'{x}_{y}_storm_trigger', looping=False)
      storm_trigger.new_condition.timer(int(time_to_storm))
      for i in range(block_size):
        for j in range(block_size):
          storm_trigger.new_effect.create_object(source_player=0,
            object_list_unit_id=OtherInfo.BONFIRE.ID,
            location_x=x+i,
            location_y=y+j)

      damage_trigger = trigger_manager.add_trigger(
          f'{x}_{y}_storm_damage_trigger', looping=True)
      damage_trigger.new_condition.timer(damage_frequency_in_seconds)
      for i in range(player_count):
        damage_trigger.new_effect.damage_object(quantity=damage_amount,
          source_player=i+1, # 0 is gaia so be 1 indexed
          area_x1=x,
          area_x2=x + added_width,
          area_y1=y,
          area_y2=y + added_width)

      # disable trigger
      damage_trigger.enabled = 0

      # add trigger for the storm_trigger to enable this
      storm_trigger.new_effect.activate_trigger(trigger_id=damage_trigger.trigger_id)

if __name__ == '__main__':
  main()
