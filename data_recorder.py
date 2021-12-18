import argparse
import json
import os
import signal
import time

import carla

from param import *
from recorder.actor_tree import ActorTree
from utils.transform import Transform, Location, Rotation
from utils.transform import transform_to_carla_transform

sig_interrupt = False


def signal_handler(signal, frame):
    global sig_interrupt
    sig_interrupt = True


class DataRecorder:
    def __init__(self, args):
        self.host = args.host
        self.port = args.port
        self.carla_client = carla.Client(self.host, self.port)
        self.carla_client.set_timeout(2.0)
        self.world = self._get_world()
        self.debug_helper = self.world.debug
        self.record_name = None
        self.base_save_dir = None
        self.world_config_file = "{}/config/{}".format(ROOT_PATH, args.world_config_file)
        self.actor_tree = ActorTree(self.world)

    def _get_world(self) -> carla.World:
        return self.carla_client.get_world()

    def destroy(self):
        self.actor_tree.destroy()

    def setting_world_and_actors(self, json_file):
        with open(json_file) as handle:
            json_settings = json.loads(handle.read())
            self.carla_client.load_world(json_settings["map"])
            settings = self.world.get_settings()
            settings.synchronous_mode = True

            if json_settings["spectator_pose"] is not None:
                pose = json_settings["spectator_pose"]
                spectator = self.world.get_spectator()
                spectator_transform = Transform(Location(pose["x"], pose["y"], pose["z"]),
                                                Rotation(roll=pose["roll"], pitch=pose["pitch"], yaw=pose["yaw"]))
                spectator.set_transform(transform_to_carla_transform(spectator_transform))

            # Make sure fixed_delta_seconds <= max_substep_delta_time * max_substeps
            world_settings = json_settings["world_settings"]
            settings.fixed_delta_seconds = world_settings["fixed_delta_seconds"]
            settings.substepping = True
            settings.max_substep_delta_time = world_settings["max_substep_delta_time"]
            settings.max_substeps = world_settings["max_substeps"]
            self.world.apply_settings(settings)

            actor_config_file = json_settings["actor_settings"]
            self.record_name = time.strftime("%Y_%m%d_%H%M", time.localtime())
            self.base_save_dir = "{}/record_{}".format(RAW_DATA_PATH, self.record_name)
            self.actor_tree = ActorTree(self.world,
                                        "{}/config/{}".format(ROOT_PATH,
                                                              actor_config_file),
                                        self.base_save_dir)
            self.actor_tree.init()

    def start_record(self):
        self.setting_world_and_actors(self.world_config_file)
        os.makedirs(self.base_save_dir, exist_ok=True)
        carla_logfile = "{}/carla_raw_record.log".format(self.base_save_dir)
        self.carla_client.start_recorder(carla_logfile)
        try:
            while True:
                # Tick Control
                self.actor_tree.tick_controller()
                # Tick World
                frame_id = self.world.tick(seconds=60.0)
                world_snapshot = self.world.get_snapshot()
                timestamp = world_snapshot.timestamp
                print("----------")
                print("World Tick -> FrameID: {} Timestamp: {}".format(frame_id, timestamp))
                # Save data to disk
                self.actor_tree.tick_data_saving(frame_id, world_snapshot)

                global sig_interrupt
                if sig_interrupt:
                    print("Exit step, wait 2 seconds...")
                    time.sleep(2.0)
                    break
        except KeyboardInterrupt:
            print("User interrupt, exit...")
        else:
            print("Unhandled error: reload the world and exit...")
        self.destroy()
        self.carla_client.reload_world()


def main():
    signal.signal(signal.SIGINT, signal_handler)
    argparser = argparse.ArgumentParser(description=__doc__)
    argparser.add_argument(
        '--host',
        metavar='H',
        default='127.0.0.1',
        help='IP of the host server (default: 127.0.0.1)')
    argparser.add_argument(
        '-p', '--port',
        metavar='P',
        default=2000,
        type=int,
        help='TCP port to listen to (default: 2000)')
    argparser.add_argument(
        '-w', '--world_config_file',
        metavar='W',
        default='world_config_template.json',
        type=str,
        help='World configuration file')
    args = argparser.parse_args()
    data_recorder = DataRecorder(args)
    data_recorder.start_record()


if __name__ == "__main__":
    # execute only if run as a script
    main()
