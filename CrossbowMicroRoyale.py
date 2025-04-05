import click
import math

from AoE2ScenarioParser.scenarios.aoe2_de_scenario import AoE2DEScenario
from AoE2ScenarioParser.datasets.other import OtherInfo

DAMAGE_FREQUENCY=1
DAMAGE_AMOUNT=3

@click.command()
@click.option('--base-map', type=click.Path(exists=True))
@click.option('--out-file', type=click.Path(exists=False))
@click.option('--map-size', type=int)
@click.option('--storm-seconds', type=int)
def main(base_map, out_file, map_size, storm_seconds):
  scenario = AoE2DEScenario.from_file(base_map)
  map_manager = scenario.map_manager
  print(map_manager)
  map_manager.map_size = map_size

  trigger_manager = scenario.trigger_manager
  add_perimeter_triggers(trigger_manager, map_size, storm_seconds)

  scenario.write_to_file(out_file)


def add_perimeter_triggers(trigger_manager, map_size, storm_seconds):
  max_distance = math.sqrt(pow(map_size/2., 2) + pow(map_size/2., 2))
  time_per_distance = storm_seconds / max_distance
  for x in range(map_size):
    for y in range(map_size):
      delta_x = abs(map_size/2 - x)
      delta_y = abs(map_size/2 - y)
      # use distance from center to calculate
      distance = math.sqrt(pow(delta_x, 2) + pow(delta_y, 2))
      time_to_storm = (max_distance - distance) * time_per_distance
      storm_trigger = trigger_manager.add_trigger(
          f'{x}_{y}_storm_trigger', looping=False)
      storm_trigger.new_condition.timer(int(time_to_storm))
      storm_trigger.new_effect.create_object(source_player=0,
        object_list_unit_id=OtherInfo.BONFIRE.ID,
        location_x=x,
        location_y=y)

      damage_trigger = trigger_manager.add_trigger(
          f'{x}_{y}_storm_damage_trigger', looping=True)
      damage_trigger.new_condition.timer(DAMAGE_FREQUENCY)
      damage_trigger.new_effect.damage_object(quantity=DAMAGE_AMOUNT,
        source_player=1, #p1
        area_x1=x,
        area_x2=x,
        area_y1=y,
        area_y2=y)
      damage_trigger.new_effect.damage_object(quantity=DAMAGE_AMOUNT,
        source_player=2, #p2
        area_x1=x,
        area_x2=x,
        area_y1=y,
        area_y2=y)
      # disable trigger
      damage_trigger.enabled = 0

      # add trigger for the storm_trigger to enable this
      storm_trigger.new_effect.activate_trigger(trigger_id=damage_trigger.trigger_id)

if __name__ == '__main__':
  main()
