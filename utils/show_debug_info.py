#!/usr/bin/python3
import argparse
import time
import carla
import sys
from pathlib import Path
sys.path.append(Path(__file__).parent.parent.as_posix())
from utils.transform import carla_transform_to_transform


def show_spawn_points(world: carla.World, debug_helper: carla.DebugHelper):
    spawn_points = world.get_map().get_spawn_points()
    for i in range(len(spawn_points)):
        carla_location = spawn_points[i].location
        bbox = carla.BoundingBox(spawn_points[i].location, carla.Vector3D(0.1, 0.1, 0.1))
        debug_helper.draw_box(bbox,
                              rotation=carla.Rotation())
        debug_helper.draw_string(carla.Location(carla_location.x,
                                                carla_location.y + 1.0,
                                                carla_location.z + 1.0),
                                 "SpawnPoint-{}".format(i),
                                 life_time=600)
    for carla_actor in world.get_actors():
        if carla_actor.type_id == 'traffic.traffic_light':
            cid = carla_actor.id
            carla_location = carla_actor.get_location()
            carla_rotation = carla_actor.get_transform().rotation
            bbox = carla.BoundingBox(carla_location,
                                     carla.Vector3D(0.5,
                                                    0.5,
                                                    0.1))
            debug_helper.draw_string(carla.Location(carla_location.x,
                                                    carla_location.y + 1.0,
                                                    carla_location.z + 1.0),
                                     "TrafficLight-{}".format(cid),
                                     color=carla.Color(0, 255, 0),
                                     life_time=600)
            debug_helper.draw_box(bbox,
                                  rotation=carla_rotation,
                                  color=carla.Color(0, 255, 0))


def main():
    argparser = argparse.ArgumentParser(description=__doc__)
    argparser.add_argument(
        '--host',
        metavar='H',
        default='localhost',
        help='IP of the host CARLA Simulator (default: localhost)')
    argparser.add_argument(
        '-p', '--port',
        metavar='P',
        default=2000,
        type=int,
        help='TCP port of CARLA Simulator (default: 2000)')
    argparser.add_argument(
        '-m', '--map',
        help='load a new map, use --list to see available maps')

    args = argparser.parse_args()
    carla_client = carla.Client(args.host, args.port)
    carla_client.set_timeout(10.0)
    carla_world = carla_client.get_world()

    if args.map is not None:
        print('load map %r.' % args.map)
        world = carla_client.load_world(args.map)

    debug = carla_world.debug
    spector = carla_world.get_spectator()

    show_spawn_points(carla_world, debug)

    try:
        while True:
            carla_transform = spector.get_transform()
            print(carla_transform_to_transform(carla_transform))
            time.sleep(0.1)
    except KeyboardInterrupt:
        carla_client.reload_world()


if __name__ == "__main__":
    # execute only if run as a script
    main()
